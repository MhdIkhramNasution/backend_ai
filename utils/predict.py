import random

labels = [
    "Fresh",
    "Almost Expired",
    "Expired"
]

def predict_image(image_path):

    prediction = random.choice(labels)

    confidence = round(random.uniform(0.80, 0.99), 2)

    return {
        "prediction": prediction,
        "confidence": confidence
    }