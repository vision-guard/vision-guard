import torch
import torch.nn as nn
import torch.nn.functional as F

class ResidualBlock3D(nn.Module):
    def __init__(self, in_channels, out_channels):
        super(ResidualBlock3D, self).__init__()
        self.conv1 = nn.Conv3d(in_channels, out_channels, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm3d(out_channels)
        self.conv2 = nn.Conv3d(out_channels, out_channels, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm3d(out_channels)
        
        self.shortcut = nn.Sequential()
        if in_channels != out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv3d(in_channels, out_channels, kernel_size=1, bias=False),
                nn.BatchNorm3d(out_channels)
            )

    def forward(self, x):
        out = F.relu(self.bn1(self.conv1(x)))
        out = self.bn2(self.conv2(out))
        out += self.shortcut(x)
        out = F.relu(out)
        return out

class TemporalAttention(nn.Module):
    def __init__(self, feature_dim):
        super(TemporalAttention, self).__init__()
        self.query = nn.Linear(feature_dim, feature_dim)
        self.key = nn.Linear(feature_dim, feature_dim)
        self.value = nn.Linear(feature_dim, feature_dim)
        self.scale = feature_dim ** -0.5

    def forward(self, x):
        # x shape: (batch, time, features)
        q = self.query(x)
        k = self.key(x)
        v = self.value(x)
        
        attn_scores = torch.matmul(q, k.transpose(-2, -1)) * self.scale
        attn_weights = F.softmax(attn_scores, dim=-1)
        
        out = torch.matmul(attn_weights, v)
        return out

class UltimateGladiator(nn.Module):
    def __init__(self, num_classes=2):
        super(UltimateGladiator, self).__init__()
        # Input: (Batch, Channels, Depth/Time, Height, Width)
        # Expected input: (B, 3, 16, 112, 112) or similar
        
        self.conv1 = nn.Conv3d(3, 64, kernel_size=(3, 7, 7), stride=(1, 2, 2), padding=(1, 3, 3))
        self.bn1 = nn.BatchNorm3d(64)
        self.pool1 = nn.MaxPool3d(kernel_size=(1, 3, 3), stride=(1, 2, 2), padding=(0, 1, 1))
        
        self.layer1 = ResidualBlock3D(64, 64)
        self.layer2 = ResidualBlock3D(64, 128)
        self.layer3 = ResidualBlock3D(128, 256)
        
        self.avgpool = nn.AdaptiveAvgPool3d((None, 1, 1)) # Output: (B, 256, T, 1, 1)
        
        self.attention = TemporalAttention(256)
        
        self.fc = nn.Linear(256, num_classes)

    def forward(self, x):
        x = F.relu(self.bn1(self.conv1(x)))
        x = self.pool1(x)
        
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        
        # (B, C, T, H, W) -> (B, C, T)
        x = self.avgpool(x).flatten(3).squeeze(3)
        
        # (B, C, T) -> (B, T, C) for attention
        x = x.permute(0, 2, 1)
        
        x = self.attention(x)
        
        # Pooling over time or just taking last? Usually pooling or last.
        # Let's mean pool over time
        x = x.mean(dim=1)
        
        x = self.fc(x)
        return x
