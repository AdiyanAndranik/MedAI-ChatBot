from setuptools import setup, find_packages
import os

setup(
    name="medAI",
    version="1.0.0",
    author="Andranik Adiyan",
    author_email="test.test@gmail.com",
    description="Medical AI Chatbot",
    long_description=open("README.md").read() if os.path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Healthcare Industry",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
    install_requires=[
        "Flask>=2.3.3",
        "Django>=4.2.7",
        "langchain>=0.0.340",
        "sentence-transformers>=2.2.2",
        # "pinecone-client>=2.2.4",
        "python-dotenv>=1.0.0",
    ],
)
