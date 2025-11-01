#!/usr/bin/env python3
"""
Train a classifier to predict whether a tangram piece needs to be slid (0) or lifted (1)

The model takes as input:
- An image of a tangram solution (as a tensor)
- A shape ID (1-7) indicating which piece we're considering

And outputs:
- A binary prediction: 0 (slide) or 1 (lift)
"""

import os
import csv
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from torchvision import models
from PIL import Image
import numpy as np
import math
import tyro
# Configuration
IMAGE_DIR = "tangram-imgs"
CSV_FILE = "tangram_annotations.csv"
BATCH_SIZE = 8
NUM_WORKERS = 4

# The 7 tangram shapes
SHAPES = [
    "Red triangle (small)",      # 1
    "Purple triangle (small)",   # 2
    "Pink triangle (medium)",    # 3
    "Orange triangle (large)",   # 4
    "Blue triangle (large)",     # 5
    "Yellow parallelogram",      # 6
    "Green square"               # 7
]


class TangramDataset(Dataset):
    """
    PyTorch Dataset for tangram classification.

    Each annotation in the CSV has 1 image with 7 shape annotations.
    This dataset expands each CSV row into 7 training examples:
    - Example 1: (image, shape_id=1) -> label for shape 1
    - Example 2: (image, shape_id=2) -> label for shape 2
    - ... and so on
    """

    def __init__(self, csv_file, image_dir, transform=None):
        """
        Args:
            csv_file (str): Path to the annotations CSV file
            image_dir (str): Directory containing the images
            transform (callable, optional): Optional transform to be applied on images
        """
        self.image_dir = image_dir
        self.transform = transform
        self.samples = []

        # Load annotations from CSV
        with open(csv_file, 'r') as f:
            reader = csv.reader(f)
            header = next(reader)  # Skip header

            for row in reader:
                if len(row) < 8:  # Need filename + 7 annotations
                    continue

                filename = row[0]
                annotations = [int(x) for x in row[1:8]]

                # Create 7 training examples from this one annotation
                for shape_id in range(1, 8):  # Shape IDs are 1-7
                    label = annotations[shape_id - 1]  # 0 or 1
                    self.samples.append({
                        'filename': filename,
                        'shape_id': shape_id,
                        'label': label
                    })

        print(f"Loaded {len(self.samples)} training examples from {len(self.samples) // 7} images")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        """
        Returns:
            image (torch.Tensor): Image tensor of shape (C, H, W)
            shape_id (int): Shape ID from 1-7
            label (int): 0 (slide) or 1 (lift)
        """
        sample = self.samples[idx]

        # Load image
        img_path = os.path.join(self.image_dir, sample['filename'])
        image = Image.open(img_path).convert('RGB')

        # Apply transforms
        if self.transform:
            image = self.transform(image)

        shape_id = sample['shape_id']
        label = sample['label']

        return image, shape_id, label


def get_default_transform(image_size=224):
    """
    Get default image transforms for the dataset.

    Args:
        image_size (int): Size to resize images to (default: 224 for ResNet)

    Returns:
        torchvision.transforms.Compose: Transform pipeline
    """
    return transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                           std=[0.229, 0.224, 0.225])  # ImageNet stats
    ])


def create_dataloaders(csv_file=CSV_FILE,
                      image_dir=IMAGE_DIR,
                      batch_size=BATCH_SIZE,
                      num_workers=NUM_WORKERS,
                      train_split=0.8,
                      image_size=224):
    """
    Create train and validation dataloaders.

    Args:
        csv_file (str): Path to annotations CSV
        image_dir (str): Directory containing images
        batch_size (int): Batch size for dataloaders
        num_workers (int): Number of worker processes for data loading
        train_split (float): Fraction of data to use for training (rest for validation)
        image_size (int): Size to resize images to

    Returns:
        train_loader, val_loader: PyTorch DataLoaders
    """
    # Create dataset
    transform = get_default_transform(image_size)
    full_dataset = TangramDataset(csv_file, image_dir, transform=transform)

    # Split into train and validation
    dataset_size = len(full_dataset)
    train_size = int(train_split * dataset_size)
    val_size = dataset_size - train_size

    train_dataset, val_dataset = torch.utils.data.random_split(
        full_dataset,
        [train_size, val_size],
        generator=torch.Generator().manual_seed(42)  # For reproducibility
    )

    # Create dataloaders
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=True
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True
    )

    print(f"Training set: {len(train_dataset)} examples")
    print(f"Validation set: {len(val_dataset)} examples")

    return train_loader, val_loader


def test_dataloader():
    """Test function to verify the dataloader works correctly"""
    print("Testing dataloader...")
    print(f"Looking for CSV file: {CSV_FILE}")
    print(f"Looking for images in: {IMAGE_DIR}")

    # Create dataloaders
    train_loader, val_loader = create_dataloaders(batch_size=4, num_workers=0)

    # Test loading a batch
    print("\nTesting train dataloader...")
    for images, shape_ids, labels in train_loader:
        print(f"Batch shape: {images.shape}")
        print(f"Shape IDs: {shape_ids}")
        print(f"Labels: {labels}")
        print(f"Image dtype: {images.dtype}")
        print(f"Image range: [{images.min():.3f}, {images.max():.3f}]")

        # Print what each example represents
        for i in range(len(images)):
            shape_name = SHAPES[shape_ids[i] - 1]
            action = "SLIDE" if labels[i] == 0 else "LIFT"
            print(f"  Example {i+1}: {shape_name} -> {action}")

        break  # Just test one batch

    print("\nDataloader test completed successfully!")

class LogisticRegression():
    def __init__(self, input_size=519, output_size=1, device="cuda"):
        # Initialize weights with small random values
        self.W = torch.randn(output_size, input_size, device=device) * 0.1  # [1, 519]
        self.b = torch.randn(output_size, device=device) * 0.1              # [1]
        self.device = device

    def forward(self, x):
        """
        Forward pass: compute sigmoid(x @ W.T + b)

        Args:
            x: [batch_size, input_size (512 + 7)]
        Returns:
            probabilities: [batch_size, output_size]
        """
        # Store input for backward pass
        self.x = x

        # Compute z = x @ W.T + b
        # W is [output_size, input_size], so W.T is [input_size, output_size]
        # x @ W.T gives [batch_size, output_size]
        self.probabilities = torch.sigmoid(x @ self.W.T + self.b) # [batch_size, 1]
        return self.probabilities

    # def backward(self, labels):
    #     """
    #     Backward pass: compute gradients manually

    #     For binary cross-entropy with sigmoid:
    #     dL/dz = (probabilities - labels)
    #     dL/dW = (probabilities - labels).T @ x
    #     dL/db = sum(probabilities - labels, axis=0)

    #     Args:
    #         labels: [batch_size, output_size] one-hot encoded labels
    #     """
    #     batch_size = self.x.shape[0]

    #     # TODO: Implement gradient computation
    #     # Hint: error = self.probabilities - labels
    #     # Hint: dW = error.T @ self.x
    #     # Hint: db = error.sum(dim=0)

    #     # Store gradients in W.grad and b.grad
    #     # YOUR CODE HERE
    #     pass


def train_classifier(
    learning_rate = 0.01,
    num_epochs = 10,
    batch_size = 8,

):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("Creating dataloaders...")
    train_loader, val_loader = create_dataloaders(batch_size=batch_size, num_workers=4) # B=8 is the batch size

    print("Instantiating model...")
    backbone_model = models.resnet18(weights=models.ResNet18_Weights.IMAGENET1K_V1)
    # Remove the final classification layer to get 512-dim features instead of 1000 classes
    backbone_model = nn.Sequential(*list(backbone_model.children())[:-1], nn.Flatten())
    backbone_model = backbone_model.to(device)
    backbone_model.eval()

    classifier_model = LogisticRegression(input_size=512 + 7, output_size=1, device=device)

    for epoch in range(num_epochs):
        for images, shape_ids, labels in train_loader:
            images = images.to(device)          # torch.Size([8, 3, 224, 224])
            shape_ids = shape_ids.to(device)    # torch.Size([8])
            labels = labels.to(device)          # torch.Size([8])

            # Extract image features using frozen ResNet
            with torch.no_grad():
                img_features = backbone_model(images) # torch.Size([8, 512])

            # Create one-hot embeddings for shape IDs
            # IMPORTANT: shape_ids are 1-7, but one_hot expects 0-6, so subtract 1!
            shape_ids_embeddings = torch.nn.functional.one_hot(shape_ids - 1, num_classes=7).float()    # torch.Size([8, 7])
            combined_input = torch.cat([img_features, shape_ids_embeddings], dim=1)                     # torch.Size([8, 519])

            outputs = classifier_model.forward(combined_input) # [8, 1]

            # Compute loss
            loss = torch.nn.functional.binary_cross_entropy(outputs, labels)
            print(f"Loss: {loss.item():.4f}")

            # Manual stochastic gradient descent update:
            error = outputs - labels                            # [batch_size, output_size]
            grad_W = (error.T @ combined_input) / batch_size    # Gradient w.r.t. weights: dL/dW = error.T @ x / batch_size
            grad_b = error.sum(dim=0) / batch_size              # Gradient w.r.t. bias: dL/db = error.sum(dim=0) / batch_size

            # SGD update: θ = θ - lr * grad
            with torch.no_grad():
                classifier_model.W -= learning_rate * grad_W
                classifier_model.b -= learning_rate * grad_b

            print(f"Gradient norm - W: {grad_W.norm().item():.4f}, b: {grad_b.norm().item():.4f}")

    print("Training completed!")

if __name__ == "__main__":
    tyro.cli(train_classifier)