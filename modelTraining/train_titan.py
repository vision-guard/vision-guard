import os
os.environ["KAGGLE_API_TOKEN"] = "KGAT_5c4890bfa554a9cef7619264f8059ea5"
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
import kagglehub
import csv
import random
from tqdm import tqdm

# --- הגדרות ---
IMG_SIZE = 112          
SEQ_LENGTH = 16         
FRAME_SKIP = 2          
BATCH_SIZE = 4          
EPOCHS = 45 
LEARNING_RATE = 2e-4 

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"🔥 Titan Training on {device}")

# ==========================================
# חלק 1: הארכיטקטורה המקורית שלך (בלי מודלים מוכנים!)
# ==========================================
class TemporalAttention(nn.Module):
    def __init__(self, hidden_size):
        super(TemporalAttention, self).__init__()
        self.attention = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.Tanh(),
            nn.Linear(hidden_size // 2, 1)
        )
    def forward(self, lstm_out):
        attn_weights = torch.softmax(self.attention(lstm_out), dim=1)
        context = torch.sum(attn_weights * lstm_out, dim=1)
        return context, attn_weights

class ResidualBlock3D(nn.Module):
    def __init__(self, in_channels, out_channels, spatial_stride=1, temporal_stride=1):
        super(ResidualBlock3D, self).__init__()
        self.conv1 = nn.Conv3d(in_channels, out_channels, kernel_size=3, 
                               stride=(temporal_stride, spatial_stride, spatial_stride), padding=1, bias=False)
        self.bn1 = nn.BatchNorm3d(out_channels)
        self.relu = nn.ReLU(inplace=True)
        self.conv2 = nn.Conv3d(out_channels, out_channels, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn2 = nn.BatchNorm3d(out_channels)
        self.shortcut = nn.Sequential()
        if spatial_stride != 1 or temporal_stride != 1 or in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv3d(in_channels, out_channels, kernel_size=1, stride=(temporal_stride, spatial_stride, spatial_stride), bias=False),
                nn.BatchNorm3d(out_channels)
            )
    def forward(self, x):
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        return self.relu(out)

class UltimateGladiator(nn.Module):
    def __init__(self):
        super(UltimateGladiator, self).__init__()
        self.conv1 = nn.Conv3d(6, 32, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm3d(32)
        self.relu = nn.ReLU(inplace=True)
        self.layer1 = self._make_layer(32, 32, 1, 1)
        self.layer2 = self._make_layer(32, 64, 2, 1)
        self.layer3 = self._make_layer(64, 128, 2, 2)
        self.layer4 = self._make_layer(128, 256, 2, 1)
        self.spatial_pool = nn.AdaptiveAvgPool3d((None, 1, 1))
        self.lstm = nn.LSTM(256, 128, num_layers=2, batch_first=True, dropout=0.4)
        self.attention = TemporalAttention(128)
        self.fc1 = nn.Linear(128, 64)
        self.fc2 = nn.Linear(64, 1)
        self.dropout = nn.Dropout(0.5)

    def _make_layer(self, in_channels, out_channels, spatial_stride, temporal_stride):
        return nn.Sequential(
            ResidualBlock3D(in_channels, out_channels, spatial_stride, temporal_stride),
            ResidualBlock3D(out_channels, out_channels, 1, 1)
        )
    def forward(self, x):
        out = self.relu(self.bn1(self.conv1(x)))
        out = self.layer1(out)
        out = self.layer2(out)
        out = self.layer3(out)
        out = self.layer4(out)
        out = self.spatial_pool(out).squeeze(-1).squeeze(-1).permute(0, 2, 1)
        lstm_out, _ = self.lstm(out)
        attn_out, _ = self.attention(lstm_out)
        return self.fc2(self.dropout(self.relu(self.fc1(attn_out))))

# ==========================================
# חלק 2: מנוע Focal Loss
# ==========================================
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

# ==========================================
# חלק 3: Augmentation קשוח וקריאת נתונים
# ==========================================
def video_transform(frames, is_training):
    if not is_training:
        return frames

    # היפוך אופקי ושינוי בהירות
    flip_h = random.random() > 0.5
    brightness_shift = random.uniform(-0.15, 0.15)
    
    # --- השדרוג: Zoom אקראי שמונע למידה של "זירת אגרוף" ---
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
            cropped = frame[y1:y1+new_h, x1:x1+new_w]
            frame = cv2.resize(cropped, (w, h))
            
        transformed_frames.append(frame)
        
    return np.array(transformed_frames)

class ViolenceDataset(Dataset):
    def __init__(self, file_paths, labels, is_training=False):
        self.file_paths = file_paths
        self.labels = labels
        self.is_training = is_training

    def __len__(self):
        return len(self.file_paths)

    def __getitem__(self, idx):
        path = self.file_paths[idx]
        label = self.labels[idx]
        
        frames = self.load_video_with_motion(path)
        frames = torch.FloatTensor(frames).permute(3, 0, 1, 2)
        return frames, torch.tensor(label, dtype=torch.float32)

    def load_video_with_motion(self, path):
        raw_frames = []
        try:
            cap = cv2.VideoCapture(path)
            if not cap.isOpened(): return np.zeros((SEQ_LENGTH, IMG_SIZE, IMG_SIZE, 6), dtype=np.float32)
            while True:
                ret, frame = cap.read()
                if not ret: break
                if frame is None or frame.size == 0: continue
                frame = cv2.resize(frame, (IMG_SIZE, IMG_SIZE))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) / 255.0
                raw_frames.append(frame)
            cap.release()
        except: return np.zeros((SEQ_LENGTH, IMG_SIZE, IMG_SIZE, 6), dtype=np.float32)
            
        if len(raw_frames) == 0: return np.zeros((SEQ_LENGTH, IMG_SIZE, IMG_SIZE, 6), dtype=np.float32)
        if len(raw_frames) > SEQ_LENGTH * FRAME_SKIP: raw_frames = raw_frames[::FRAME_SKIP]
        if len(raw_frames) > SEQ_LENGTH: raw_frames = raw_frames[:SEQ_LENGTH]
            
        raw_frames = video_transform(np.array(raw_frames), self.is_training)

        combined_frames = []
        for i in range(len(raw_frames)):
            curr_frame = raw_frames[i]
            prev_frame = curr_frame if i == 0 else raw_frames[i-1]
            motion_diff = np.abs(curr_frame - prev_frame)
            combined_frames.append(np.concatenate([curr_frame, motion_diff], axis=-1))
            
        combined_frames = np.array(combined_frames)
        if len(combined_frames) < SEQ_LENGTH:
            padding = np.zeros((SEQ_LENGTH - len(combined_frames), IMG_SIZE, IMG_SIZE, 6))
            combined_frames = np.concatenate((combined_frames, padding))
        return combined_frames

# --- השדרוג הענק: איסוף מסיבי של סרטוני עלית ---
def get_massive_datasets():
    print("🌍 Downloading Elite Datasets (Street, CCTV, Sports, Aggression)...")
    paths, labels = [], []
    
    # 1. הדאטאסט המקורי (מכות רחוב וחיים אמיתיים)
    dir1 = kagglehub.dataset_download("mohamedmustafa/real-life-violence-situations-dataset")
    
    # 3. דאטאסט עיר חכמה (זווית מצלמות אבטחה אמיתיות) - הבחירה שלך!
    dir3 = kagglehub.dataset_download("toluwaniaremu/smartcity-cctv-violence-detection-dataset-scvd")
    
    # 4. התנהגות אגרסיבית (מרחיב את סוגי האלימות) - הבחירה שלך!
    dir4 = kagglehub.dataset_download("trainingdatapro/aggressive-behavior-video-classification")
    
    directories = [dir1, dir3, dir4]
    
    for data_dir in directories:
        for root, dirs, files in os.walk(data_dir):
            label = None
            lower_root = root.lower()
            
            # שלב א': חיפוש תיקיות בטוחות (חשוב שזה יהיה ראשון בגלל מילים כמו non-violence)
            if any(x in lower_root for x in ["nonviolence", "non-violence", "safe", "nonfight", "nofight", "normal", "non-aggressive", "non_aggressive"]):
                label = 0
            # שלב ב': חיפוש תיקיות אלימות
            elif any(x in lower_root for x in ["violence", "fight", "aggressive"]):
                label = 1
                
            if label is not None:
                for f in files:
                    if f.lower().endswith(('.mp4', '.avi', '.mov')):
                        paths.append(os.path.join(root, f))
                        labels.append(label)
                        
    print(f"📥 TOTAL Elite Videos Gathered for Training: {len(paths)}")
    return paths, labels
# ==========================================
# חלק 4: אימון Titan (עם הדאטא המורחב)
# ==========================================
def train_titan():
    print("⚔️ Launching TITAN V3 - FRESH START (Zero Knowledge)")
    
    # איסוף הנתונים (7643 סרטונים!)
    files, labels = get_massive_datasets()
    
    X_train, X_val, y_train, y_val = train_test_split(files, labels, test_size=0.2, random_state=42)
    
    train_ds = ViolenceDataset(X_train, y_train, is_training=True)
    val_ds = ViolenceDataset(X_val, y_val, is_training=False)
    
    # העליתי טיפה את ה-Batch Size ל-8 אם יש לך כרטיס מסך חזק, אם לא - תשאיר 4.
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False)
    
    # יצירת המודל מ-0
    model = UltimateGladiator().to(device)
    print("🆕 Model initialized with random weights. Training from scratch...")

    # Focal Loss - נשארים עם הפרמטרים המנצחים
    criterion = FocalLoss(alpha=0.25, gamma=2.0)
    
    # אופטימייזר AdamW - מעולה למניעת Overfitting
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-3)
    
    # סקדולר - גלי קוסינוס לחיפוש עמקים גלובליים
    scheduler = optim.lr_scheduler.CosineAnnealingWarmRestarts(optimizer, T_0=10, T_mult=2, eta_min=1e-6)
    
    best_acc = 0
    csv_filename = "titan_v3_scratch_log.csv"
    
    # יצירת קובץ לוג חדש
    with open(csv_filename, mode='w', newline='') as file:
        csv.writer(file).writerow(['epoch', 'accuracy', 'loss', 'val_accuracy', 'val_loss'])
    
    for epoch in range(EPOCHS):
        model.train()
        train_loss, correct, total = 0, 0, 0
        loop = tqdm(train_loader, desc=f"Epoch {epoch}/{EPOCHS-1}")
        
        for inputs, targets in loop:
            inputs, targets = inputs.to(device), targets.to(device).unsqueeze(1)
            optimizer.zero_grad()
            
            outputs = model(inputs)
            loss = criterion(outputs, targets)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            predicted = (torch.sigmoid(outputs) > 0.5).float()
            correct += (predicted == targets).sum().item()
            total += targets.size(0)
            loop.set_postfix(loss=loss.item(), acc=100*correct/total)
            
        train_acc_final = correct / total
        train_loss_final = train_loss / len(train_loader)
            
        # בדיקה על נתוני המבחן (Validation)
        model.eval()
        val_loss, val_correct, val_total = 0, 0, 0
        with torch.no_grad():
            for inputs, targets in val_loader:
                inputs, targets = inputs.to(device), targets.to(device).unsqueeze(1)
                outputs = model(inputs)
                loss = criterion(outputs, targets)
                val_loss += loss.item()
                val_correct += ((torch.sigmoid(outputs) > 0.5).float() == targets).sum().item()
                val_total += targets.size(0)
                
        val_acc_final = val_correct / val_total
        val_loss_final = val_loss / len(val_loader)
        
        scheduler.step()
        
        print(f"📊 Validation -> Loss: {val_loss_final:.4f} | Accuracy: {val_acc_final*100:.2f}%")
        
        # שמירת המודל הכי טוב
        if val_acc_final > best_acc:
            best_acc = val_acc_final
            torch.save(model.state_dict(), "titan_v3_best.pth")
            print(f"💾 Saved new champion with {val_acc_final*100:.2f}% accuracy!")
        
        # רישום ללוג
        with open(csv_filename, mode='a', newline='') as file:
            csv.writer(file).writerow([epoch, train_acc_final, train_loss_final, val_acc_final, val_loss_final])
if __name__ == "__main__":
    train_titan()