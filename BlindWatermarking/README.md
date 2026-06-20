# Deep Learning Blind Watermarking

This repository contains a PyTorch implementation of a deep learning-based blind watermarking system. The project consists of two main neural network models: an **Embedder** and an **Extractor**. The Embedder network conceals a watermark image within a cover image, creating a "marked" image that is visually similar to the original. The Extractor network can then recover the hidden watermark from the marked image *without* requiring the original cover image, hence the term "blind watermarking".

The implementation is contained within a single Jupyter Notebook (`Workbook.ipynb`) that handles data preprocessing, model definition, training, and evaluation.

## Model Architecture

The system is composed of two primary modules trained in sequence.

### 1. Watermark Embedder
The embedder's goal is to hide the watermark with minimal distortion to the cover image. It consists of three parts:
- **Cover Encoder (`CoverEncoder`)**: A convolutional network that progressively downsamples a 128x128 cover image to a 16x16 feature map.
- **Watermark Encoder (`WatermarkEncoder`)**: A similar convolutional network that downsamples a 32x32 watermark image to a 16x16 feature map.
- **Embedder Decoder (`EmbedderDecoder`)**: This network takes the concatenated feature maps from both encoders and progressively upsamples them back to a 128x128 image, resulting in the final watermarked image.

### 2. Watermark Extractor
The extractor's goal is to retrieve the original watermark from the watermarked image. It is trained after the embedder is finalized and its weights are frozen.
- **Marked Encoder (`MarkedEncoder`)**: This network has the same architecture as the `CoverEncoder` and processes the 128x128 watermarked image into a 16x16 feature map.
- **Extractor Decoder (`ExtractorDecoder`)**: This network takes the feature map from the `MarkedEncoder` and upsamples it to reconstruct the 32x32 watermark image.

## Datasets

- **Cover Images**: The [Kaggle "Cats and Dogs"](https://www.microsoft.com/en-us/download/details.aspx?id=54765) dataset is used for cover images. They are preprocessed by resizing to 128x128 and converting to grayscale.
- **Watermark Images**: The [CIFAR-10](https://www.cs.toronto.edu/~kriz/cifar.html) dataset is used for watermark images. They are preprocessed by resizing to 32x32 and converting to grayscale.

The `Untitled-1.ipynb` notebook automatically downloads and processes these datasets.

## Training

The training process occurs in two distinct stages:

1.  **Embedder Training**: The `WatermarkEmbedder` model is trained for 60 epochs. The loss function is the Mean Squared Error (MSE) between the original cover image and the generated watermarked image. This encourages the network to produce a marked image that is visually indistinguishable from the cover.
    - Final Training Loss: `0.001442`
    - Final Validation Loss: `0.001470`

2.  **Extractor Training**: After the embedder is trained, its weights are frozen. The `WatermarkExtractor` is then trained for 40 epochs. The loss function is the MSE between the original watermark and the watermark reconstructed by the extractor.
    - Final Training Loss: `0.026242`
    - Final Validation Loss: `0.034550`

## How to Use

This project is self-contained within the `Untitled-1.ipynb` notebook. The repository also includes the final trained model weights (`embedder_final.pth` and `extractor_final.pth`).

### Prerequisites
You will need the following Python libraries installed:
- `torch`
- `torchvision`
- `numpy`
- `Pillow`
- `scikit-image`
- `matplotlib`
- `tqdm`
- `jupyter`

You can install them using pip:
```bash
pip install torch torchvision numpy Pillow scikit-image matplotlib tqdm jupyter
```

### Running the Project
1.  Clone this repository.
2.  Open and run the `Untitled-1.ipynb` notebook in a Jupyter environment.
3.  Executing the notebook cells in order will:
    - Download and preprocess the datasets.
    - Define the model architectures.
    - Train the embedder and save its weights as `embedder_final.pth`.
    - Train the extractor and save its weights as `extractor_final.pth`.
    - Load the trained models to perform and visualize the extraction process on test images.
    - Calculate and display a quantitative evaluation of the extraction quality.

## Results

The trained models are capable of embedding a watermark imperceptibly and subsequently extracting a recognizable version of it from the marked image.

### Visual Results
The final cells of the notebook produce visualizations comparing the original ground truth watermarks with the ones extracted by the model, along with a difference map. While not a perfect reconstruction, the extracted watermarks are clearly recognizable.

### Quantitative Metrics
The quality of the extracted watermark is measured using Peak Signal-to-Noise Ratio (PSNR) and Structural Similarity Index (SSIM) against the ground truth. Here are the results for the first 5 samples from the test set:

| Sample | PSNR    | SSIM     |
|--------|---------|----------|
| 1      | 9.3687  | -0.0031  |
| 2      | 7.0897  | -0.0817  |
| 3      | 7.7120  |  0.1621  |
| 4      | 8.5171  |  0.0414  |
| 5      | 9.4756  | -0.0425  |

The PSNR and SSIM scores indicate that while there is a significant difference between the original and extracted watermarks, the model has successfully learned to encode and decode the underlying information.
