import os
import cv2
import torch
from torch.utils.data import Dataset
import torchvision.datasets as datasets
import torchvision.transforms as T


# =============================
# Cover Dataset
# =============================
class CoverDataset(Dataset):

    def __init__(self, folder):
        self.files = []

        for root, _, files in os.walk(folder):
            for f in files:
                if f.lower().endswith((".jpg", ".png", ".jpeg")):
                    self.files.append(os.path.join(root, f))

        self.files.sort()  # 🔥 ensures reproducibility

    def __len__(self):
        return len(self.files)

    def __getitem__(self, idx):

        img = cv2.imread(self.files[idx], cv2.IMREAD_GRAYSCALE)

        if img is None:
            return self.__getitem__((idx + 1) % len(self))
        
        img = cv2.resize(img, (256, 256))

        img = img.astype("float32") / 255.0

        # (H, W) → (1, H, W)
        img = torch.from_numpy(img).unsqueeze(0)

        return img


# =============================
# Logo Watermark Dataset
# =============================
def load_logo_watermarks():

    transform = T.Compose([
        T.Grayscale(num_output_channels=1),  # 🔥 FORCE SINGLE CHANNEL
        T.Resize((128, 128)),
        T.ToTensor()
    ])

    dataset = datasets.ImageFolder(
        root="dataset/logos_128",   # folder must contain class subfolder (logo/)
        transform=transform
    )

    return dataset
