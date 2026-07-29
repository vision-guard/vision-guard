import os
import subprocess
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.metrics import f1_score, precision_score, recall_score, confusion_matrix, classification_report, roc_curve, auc, precision_recall_curve, average_precision_score
import kagglehub
import csv
import random
from tqdm import tqdm
import matplotlib.pyplot as plt
import seaborn as sns

os.environ["KAGGLE_API_TOKEN"] = "KGAT_5c4890bfa554a9cef7619264f8059ea5"

IMG_SIZE = 112
SEQ_LENGTH = 16
FRAME_SKIP = 2

BATCH_SIZE = 4
EPOCHS = 30
LEARNING_RATE = 1e-4

print("StreamSentinel training configured.")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"🚀 Training on {device}")


class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=50):
        super(PositionalEncoding, self).__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x):
        return x + self.pe[:, :x.size(1), :].to(x.device)


class ConvSpatialExtractor(nn.Module):
    def __init__(self):
        super(ConvSpatialExtractor, self).__init__()
        self.features = nn.Sequential(
            nn.Conv2d(6, 32, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
            nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(kernel_size=2, stride=2),
            nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d((1, 1)),
        )

    def forward(self, x):
        return self.features(x).view(x.size(0), -1)


class StreamSentinelViT(nn.Module):
    def __init__(self, embed_dim=128, num_heads=4, num_layers=2, seq_length=16):
        super(StreamSentinelViT, self).__init__()
        self.spatial_extractor = ConvSpatialExtractor()
        self.pos_encoder = PositionalEncoding(embed_dim, max_len=seq_length)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=embed_dim,
            nhead=num_heads,
            dim_feedforward=embed_dim * 4,
            dropout=0.3,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.classifier = nn.Sequential(
            nn.Linear(embed_dim, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(0.4),
            nn.Linear(64, 1),
        )

    def forward(self, x):
        b, c, t, h, w = x.size()
        x = x.permute(0, 2, 1, 3, 4).reshape(b * t, c, h, w)
        spatial_features = self.spatial_extractor(x)
        x = spatial_features.view(b, t, -1)
        x = self.pos_encoder(x)
        x = self.transformer(x)
        x = x.mean(dim=1)
        return self.classifier(x)


class FocalLoss(nn.Module):
    def __init__(self, alpha=0.25, gamma=2.0):
        super(FocalLoss, self).__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.bce_with_logits = nn.BCEWithLogitsLoss(reduction='none')

    def forward(self, inputs, targets):
        bce_loss = self.bce_with_logits(inputs, targets)
        pt = torch.exp(-bce_loss)
        focal_loss = self.alpha * (1 - pt) ** self.gamma * bce_loss
        return focal_loss.mean()


def video_transform(frames, is_training):
    if not is_training:
        return frames

    flip_h = random.random() > 0.5
    brightness_shift = random.uniform(-0.15, 0.15)
    do_zoom = random.random() > 0.5
    zoom_factor = random.uniform(0.7, 0.95) if do_zoom else 1.0

    transformed_frames = []
    for frame in frames:
        if flip_h:
            frame = cv2.flip(frame, 1)

        frame = frame + brightness_shift
        frame = np.clip(frame, 0.0, 1.0)

        if do_zoom:
            h, w = frame.shape[:2]
            new_h, new_w = int(h * zoom_factor), int(w * zoom_factor)
            y1, x1 = (h - new_h) // 2, (w - new_w) // 2
            cropped = frame[y1:y1 + new_h, x1:x1 + new_w]
            frame = cv2.resize(cropped, (w, h))

        transformed_frames.append(frame)

    return np.array(transformed_frames)


class ViolenceDataset(Dataset):
    def __init__(self, file_paths, labels, is_training=False, stride=None):
        self.is_training = is_training
        self.required_raw_frames = SEQ_LENGTH * FRAME_SKIP
        if stride is None:
            self.stride = self.required_raw_frames // 2 if is_training else self.required_raw_frames
        else:
            self.stride = stride

        self.samples = []
        for path, label in tqdm(zip(file_paths, labels), total=len(file_paths), desc="Slicing Windows"):
            cap = cv2.VideoCapture(path)
            if not cap.isOpened():
                continue
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()

            if total_frames <= 0:
                continue

            if total_frames < self.required_raw_frames:
                self.samples.append((path, 0, label))
            else:
                for start_frame in range(0, total_frames - self.required_raw_frames + 1, self.stride):
                    self.samples.append((path, start_frame, label))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, start_frame, label = self.samples[idx]
        frames = self.load_video_chunk(path, start_frame)
        frames = torch.FloatTensor(frames).permute(3, 0, 1, 2)
        return frames, torch.tensor(label, dtype=torch.float32)

    def load_video_chunk(self, path, start_frame):
        raw_frames = []
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return np.zeros((SEQ_LENGTH, IMG_SIZE, IMG_SIZE, 6), dtype=np.float32)

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        count = 0
        while count < self.required_raw_frames:
            ret, frame = cap.read()
            if not ret or frame is None or frame.size == 0:
                break

            if count % FRAME_SKIP == 0:
                frame = cv2.resize(frame, (IMG_SIZE, IMG_SIZE))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) / 255.0
                raw_frames.append(frame)

            count += 1

        cap.release()

        if len(raw_frames) == 0:
            return np.zeros((SEQ_LENGTH, IMG_SIZE, IMG_SIZE, 6), dtype=np.float32)

        raw_frames = video_transform(np.array(raw_frames), self.is_training)

        combined_frames = []
        for i in range(len(raw_frames)):
            curr_frame = raw_frames[i]
            prev_frame = curr_frame if i == 0 else raw_frames[i - 1]
            motion_diff = np.abs(curr_frame - prev_frame)
            combined_frames.append(np.concatenate([curr_frame, motion_diff], axis=-1))

        combined_frames = np.array(combined_frames)
        if len(combined_frames) < SEQ_LENGTH:
            padding = np.zeros((SEQ_LENGTH - len(combined_frames), IMG_SIZE, IMG_SIZE, 6), dtype=np.float32)
            combined_frames = np.concatenate((combined_frames, padding), axis=0)

        return combined_frames


def get_massive_datasets():
    print("Downloading and indexing datasets (Street, CCTV, SCVD, RWF)...")
    paths, labels = [], []

    dir1 = kagglehub.dataset_download("mohamedmustafa/real-life-violence-situations-dataset")
    dir3 = kagglehub.dataset_download("toluwaniaremu/smartcity-cctv-violence-detection-dataset-scvd")
    dir4 = kagglehub.dataset_download("trainingdatapro/aggressive-behavior-video-classification")

    print("Pulling a clean, uncorrupted RWF-2000 mirror dataset via CLI...")
    rwf_clean_dir = os.path.join(os.path.expanduser("~"), "rwf2000_clean")
    if not os.path.exists(rwf_clean_dir):
        os.makedirs(rwf_clean_dir, exist_ok=True)
        subprocess.run([
            "kaggle",
            "datasets",
            "download",
            "-d",
            "canerbykl/rwf2000-video-dataset",
            "--unzip",
            "-p",
            rwf_clean_dir,
        ], check=False)

    directories = [dir1, dir3, dir4, rwf_clean_dir]

    for data_dir in directories:
        for root, dirs, files in os.walk(data_dir):
            label = None
            lower_root = root.lower()

            if any(x in lower_root for x in ["nonviolence", "non-violence", "safe", "nonfight", "nofight", "normal", "non-aggressive", "non_aggressive"]):
                label = 0
            elif any(x in lower_root for x in ["violence", "fight", "aggressive", "assault", "abuse", "robbery", "shooting"]):
                label = 1

            if label is not None:
                for f in files:
                    if f.lower().endswith((".mp4", ".avi", ".mov", ".mkv")):
                        original_path = os.path.join(root, f)
                        paths.append(original_path)
                        labels.append(label)

    print(f"Total clean, functional video paths cached: {len(paths)}")
    return paths, labels


def train_titan():
    print("⚔️ Launching StreamSentinel training")

    files, labels = get_massive_datasets()

    X_train, X_temp, y_train, y_temp = train_test_split(files, labels, test_size=0.3, random_state=42)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)

    print("\n--- PATH SPLIT DISTRIBUTION ---")
    print(f"Training Video Files: {len(X_train)}")
    print(f"Validation Video Files: {len(X_val)}")
    print(f"Testing Video Files: {len(X_test)}")

    print("\nSlicing videos into sliding temporal windows (This may take a few minutes)...")
    train_dataset = ViolenceDataset(X_train, y_train, is_training=True)
    val_dataset = ViolenceDataset(X_val, y_val, is_training=False)
    test_dataset = ViolenceDataset(X_test, y_test, is_training=False)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=2, pin_memory=True)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=2, pin_memory=True)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=2, pin_memory=True)

    video_batch, label_batch = next(iter(train_loader))
    print("\n--- PIPELINE VERIFICATION SUCCESSFUL ---")
    print(f"Total Temporal Windows for Training: {len(train_dataset)}")
    print(f"Total Temporal Windows for Validation: {len(val_dataset)}")
    print(f"Total Temporal Windows for Testing: {len(test_dataset)}")
    print(f"Video Batch Tensor Shape [Batch, Channels, Time, Height, Width]: {video_batch.shape}")
    print(f"Label Batch Tensor Shape: {label_batch.shape}")

    model = StreamSentinelViT().to(device)
    criterion = FocalLoss(alpha=0.25, gamma=2.0)
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-3)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=30, eta_min=1e-6)

    num_epochs = EPOCHS
    best_f1 = 0.0
    history = {
        'train_loss': [], 'val_loss': [],
        'train_acc': [], 'val_acc': [],
        'train_f1': [], 'val_f1': [],
        'train_precision': [], 'val_precision': [],
        'train_recall': [], 'val_recall': []
    }

    print(f"🚀 Launching Training on {device}...")

    for epoch in range(num_epochs):
        model.train()
        running_loss = 0.0
        train_preds, train_targets = [], []

        train_bar = tqdm(train_loader, desc=f"Epoch {epoch + 1}/{num_epochs}")
        for inputs, targets in train_bar:
            inputs, targets = inputs.to(device), targets.to(device)

            optimizer.zero_grad()
            outputs = model(inputs).squeeze(1)
            loss = criterion(outputs, targets)
            loss.backward()

            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            running_loss += loss.item()
            probs = torch.sigmoid(outputs)
            preds = (probs >= 0.5).float()
            train_preds.extend(preds.detach().cpu().numpy())
            train_targets.extend(targets.detach().cpu().numpy())

            train_bar.set_postfix(loss=f"{loss.item():.4f}")

        epoch_train_loss = running_loss / len(train_loader)
        train_acc = (np.array(train_preds) == np.array(train_targets)).mean()
        train_f1 = f1_score(train_targets, train_preds, zero_division=0)
        train_prec = precision_score(train_targets, train_preds, zero_division=0)
        train_rec = recall_score(train_targets, train_preds, zero_division=0)

        model.eval()
        val_loss = 0.0
        val_preds, val_targets = [], []

        with torch.no_grad():
            for inputs, targets in val_loader:
                inputs, targets = inputs.to(device), targets.to(device)
                outputs = model(inputs).squeeze(1)
                loss = criterion(outputs, targets)
                val_loss += loss.item()

                probs = torch.sigmoid(outputs)
                preds = (probs >= 0.5).float()
                val_preds.extend(preds.cpu().numpy())
                val_targets.extend(targets.cpu().numpy())

        scheduler.step()

        val_loss_epoch = val_loss / len(val_loader)
        val_acc = (np.array(val_preds) == np.array(val_targets)).mean()
        val_f1 = f1_score(val_targets, val_preds, zero_division=0)
        val_prec = precision_score(val_targets, val_preds, zero_division=0)
        val_rec = recall_score(val_targets, val_preds, zero_division=0)

        print(f"📊 Val Loss: {val_loss_epoch:.4f} | Acc: {val_acc * 100:.2f}% | F1: {val_f1:.4f} | Prec: {val_prec:.4f} | Rec: {val_rec:.4f}")

        history['train_loss'].append(epoch_train_loss)
        history['val_loss'].append(val_loss_epoch)
        history['train_acc'].append(train_acc)
        history['val_acc'].append(val_acc)
        history['train_f1'].append(train_f1)
        history['val_f1'].append(val_f1)
        history['train_precision'].append(train_prec)
        history['val_precision'].append(val_prec)
        history['train_recall'].append(train_rec)
        history['val_recall'].append(val_rec)

        if val_f1 > best_f1:
            best_f1 = val_f1
            torch.save(model.state_dict(), "sentinel_best_f1.pth")
            print(f"💾 Checkpoint Saved! Best validation F1 enhanced to: {best_f1:.4f}\n")

    sns.set_theme(style="whitegrid")
    epochs = range(1, len(history['train_loss']) + 1)

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes[0, 0].plot(epochs, history['train_loss'], 'b-o', label='Training Loss', linewidth=2, markersize=4)
    axes[0, 0].plot(epochs, history['val_loss'], 'r-s', label='Validation Loss', linewidth=2, markersize=4)
    axes[0, 0].set_title('💥 Focal Loss Convergence', fontsize=13, fontweight='bold')
    axes[0, 0].set_xlabel('Epochs')
    axes[0, 0].set_ylabel('Loss Value')
    axes[0, 0].legend()

    axes[0, 1].plot(epochs, history['train_f1'], 'b-o', label='Training F1-Score', linewidth=2, markersize=4)
    axes[0, 1].plot(epochs, history['val_f1'], 'm-d', label='Validation F1-Score', linewidth=2, markersize=4)
    axes[0, 1].set_title('📈 F1-Score (Overfitting Check)', fontsize=13, fontweight='bold')
    axes[0, 1].set_xlabel('Epochs')
    axes[0, 1].set_ylabel('F1-Score (0-1)')
    axes[0, 1].legend()

    axes[1, 0].plot(epochs, history['train_acc'], 'b-o', label='Training Accuracy', linewidth=2, markersize=4)
    axes[1, 0].plot(epochs, history['val_acc'], 'g-^', label='Validation Accuracy', linewidth=2, markersize=4)
    axes[1, 0].set_title('⚖️ Accuracy Trajectory', fontsize=13, fontweight='bold')
    axes[1, 0].set_xlabel('Epochs')
    axes[1, 0].set_ylabel('Accuracy')
    axes[1, 0].legend()

    axes[1, 1].plot(epochs, history['val_precision'], 'c-x', label='Validation Precision (False Alarms)', linewidth=2)
    axes[1, 1].plot(epochs, history['val_recall'], 'y-+', label='Validation Recall (Missed Detections)', linewidth=2)
    axes[1, 1].set_title('🎯 Precision vs. Recall Dynamics', fontsize=13, fontweight='bold')
    axes[1, 1].set_xlabel('Epochs')
    axes[1, 1].set_ylabel('Score (0-1)')
    axes[1, 1].legend()

    plt.tight_layout()
    plt.show()

    def evaluate_on_test_set(model_class, loader, device):
        model = model_class().to(device)
        model.load_state_dict(torch.load("sentinel_best_f1.pth", map_location=device, weights_only=True))
        model.eval()

        test_preds, test_probs, test_targets = [], [], []

        print("🔮 Running final inference on completely isolated Test Video Windows...")
        with torch.no_grad():
            for inputs, targets in tqdm(loader, desc="Testing Partition"):
                inputs = inputs.to(device)
                outputs = model(inputs).squeeze(1)

                probs = torch.sigmoid(outputs).cpu().numpy()
                preds = (probs >= 0.5).astype(int)

                test_probs.extend(probs)
                test_preds.extend(preds)
                test_targets.extend(targets.numpy())

        print("\n========= 📝 CRITICAL TESTING PERFORMANCE REPORT =========")
        print(classification_report(test_targets, test_preds, target_names=["Normal/Safe Context", "Violence/Fight Case"]))

        fig, axes = plt.subplots(1, 3, figsize=(20, 5))
        cm = confusion_matrix(test_targets, test_preds)
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', cbar=False, ax=axes[0],
                    xticklabels=["Normal", "Violence"], yticklabels=["Normal", "Violence"], annot_kws={"size": 14})
        axes[0].set_title('🎯 Confusion Matrix', fontsize=13, fontweight='bold')
        axes[0].set_xlabel('Predicted Categorization')
        axes[0].set_ylabel('Ground-Truth Label')

        fpr, tpr, _ = roc_curve(test_targets, test_probs)
        roc_auc = auc(fpr, tpr)
        axes[1].plot(fpr, tpr, color='darkorange', lw=2.5, label=f'ROC AUC = {roc_auc:.4f}')
        axes[1].plot([0, 1], [0, 1], color='navy', lw=1.5, linestyle='--')
        axes[1].set_xlim([0.0, 1.0])
        axes[1].set_ylim([0.0, 1.05])
        axes[1].set_title('🛡️ ROC Curve', fontsize=13, fontweight='bold')
        axes[1].set_xlabel('False Positive Rate')
        axes[1].set_ylabel('True Positive Rate')
        axes[1].legend(loc="lower right")

        precision, recall, _ = precision_recall_curve(test_targets, test_probs)
        pr_auc = average_precision_score(test_targets, test_probs)
        axes[2].plot(recall, precision, color='purple', lw=2.5, label=f'PR AUC = {pr_auc:.4f}')
        axes[2].set_xlim([0.0, 1.0])
        axes[2].set_ylim([0.0, 1.05])
        axes[2].set_title('🚨 Precision-Recall Curve', fontsize=13, fontweight='bold')
        axes[2].set_xlabel('Recall (Found Violence)')
        axes[2].set_ylabel('Precision (True Violence)')
        axes[2].legend(loc="lower left")

        plt.tight_layout()
        plt.show()

    evaluate_on_test_set(StreamSentinelViT, test_loader, device)


if __name__ == "__main__":
    train_titan()
