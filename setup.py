"""
Setup configuration for Clinical Trial Control Tower
"""

from setuptools import setup, find_packages

# Read README for long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read requirements
with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="clinical-trial-control-tower",
    version="1.0.0",
    author="Team Zenith",
    author_email="team@zenith.local",
    description="Enterprise Clinical Trial Management System with AI and Blockchain",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/clinical-trial-portal",
    packages=find_packages(where="backend"),
    package_dir={"": "backend"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Healthcare Industry",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
        "License :: Other/Proprietary License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Framework :: Django :: 5.0",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-django>=4.7.0",
            "black>=23.12.1",
            "flake8>=7.0.0",
        ],
        "ml": [
            "torch>=2.1.2",
            "scikit-learn>=1.3.2",
        ],
    },
    entry_points={
        "console_scripts": [
            "ctct-import=management.commands.import_study_data:main",
            "ctct-metrics=management.commands.compute_metrics:main",
        ],
    },
)
