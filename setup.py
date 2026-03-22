from setuptools import setup, find_packages

setup(
    name="skinai-data",
    version="0.1.0",
    description="AI Hub 08-14 안면부 피부질환 데이터셋 PyTorch DataLoader",
    packages=find_packages(include=["skinai_data", "skinai_data.*"]),
    python_requires=">=3.8",
    install_requires=[
        "torch>=2.0",
        "torchvision",
        "google-api-python-client",
        "google-auth-httplib2",
        "google-auth-oauthlib",
        "pandas",
        "Pillow",
        "tqdm",
        "python-dotenv",
    ],
)
