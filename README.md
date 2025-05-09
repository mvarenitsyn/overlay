# Image Edits API

A powerful Flask-based REST API for intelligent image manipulation.

## Features

- **Smart Resizing**: Automatically crops images to desired aspect ratios while preserving important visual content using OpenCV saliency detection
- **Advanced Overlays**: Apply customizable overlays to images with control over:
  - Shape (rectangle or ellipse)
  - Border styles and colors
  - Background images with different fitting modes
  - Shadows and glows with adjustable properties
- **Flexible Output**: Control image format and quality

## API Endpoints

### Health Check

```
GET /health
```

Returns "ok" if the service is running.

### Resize Image

```
POST /v1/resize
```

Intelligently resizes an image to a target aspect ratio while preserving important visual content.

Example request:
```json
{
  "baseImage": {
    "source": "url",
    "data": "https://example.com/image.jpg"
  },
  "ratio": "16:9",
  "saliency": {
    "threshold": 0.3,
    "minCrop": 0.6
  },
  "mode": "cover",
  "output": {
    "format": "jpeg",
    "quality": 90
  }
}
```

### Render Overlays

```
POST /v1/render
```

Applies custom overlays to a base image.

Example request:
```json
{
  "baseImage": {
    "source": "url",
    "data": "https://example.com/image.jpg"
  },
  "overlays": [
    {
      "shape": "rectangle",
      "paddingFromCenter": {"x": 0, "y": 0},
      "size": {"w": 300, "h": 200},
      "border": {
        "color": "rgba(255, 255, 255, 0.8)",
        "thickness": 3
      },
      "background": {
        "source": "url",
        "data": "https://example.com/overlay.png",
        "fit": "cover"
      },
      "shadow": {
        "type": "drop",
        "color": "rgba(0, 0, 0, 0.5)",
        "blur": 10,
        "offset": {"x": 5, "y": 5}
      }
    }
  ],
  "output": {
    "format": "png"
  }
}
```

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install Flask Pillow requests opencv-python numpy
   ```
3. Run the application:
   ```
   python api.py
   ```

## Deployment

This project is configured for easy deployment on Railway. Simply connect your repository and Railway will automatically deploy the application.

## Requirements

- Python 3.7+
- Flask
- Pillow
- Requests
- OpenCV
- NumPy
