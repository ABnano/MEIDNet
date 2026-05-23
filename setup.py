from setuptools import setup, find_packages

setup(
    name="meidnet",
    version="1.0.0",
    description="Property-conditioned constrained inverse design for cubic ABX3 perovskites",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="MEIDNet Contributors",
    url="https://github.com/ABnano/MEIDNet",
    packages=find_packages(exclude=["scripts*", "tools*", "results*"]),
    python_requires=">=3.9",
    install_requires=[
        "torch>=2.0.0",
        "pymatgen>=2024.1.1",
        "scikit-learn>=1.3",
        "matplotlib>=3.7",
        "pandas>=2.0",
        "numpy>=1.24",
    ],
    extras_require={
        "stability": ["ase>=3.22", "mace-torch>=0.3.6"],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Topic :: Scientific/Engineering :: Chemistry",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
