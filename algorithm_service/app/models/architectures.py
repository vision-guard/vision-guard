import torch
import torch.nn as nn

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