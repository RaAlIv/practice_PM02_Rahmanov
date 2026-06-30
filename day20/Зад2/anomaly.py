import os
import numpy as np
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

def gen_normal_distribution(mu, sigma, size, range=(0, 1), max_val=1):
    bins = np.linspace(*range, size)
    result = 1 / (sigma * np.sqrt(2*np.pi)) * np.exp(-(bins - mu)**2 / (2*sigma**2))
    cur_max_val = result.max()
    k = max_val / cur_max_val
    result *= k
    return result


dist = gen_normal_distribution(0.3, 0.05, 256, max_val=1)
print(f"Max value: {dist.max()}")

plt.figure(figsize=(10, 4))
plt.plot(np.linspace(0, 1, 256), dist)
plt.title("Sample Normal Distribution")
plt.show()


in_distribution_size = 2000
out_distribution_size = 200
val_size = 100
sample_size = 256

random_generator = np.random.RandomState(seed=42)

def generate_in_samples(size, sample_size):
    in_samples = np.zeros((size, sample_size))
    
    in_mus = random_generator.uniform(0.1, 0.9, size)
    in_sigmas = random_generator.uniform(0.05, 0.5, size)
    for i in range(size):
        in_samples[i] = gen_normal_distribution(in_mus[i], in_sigmas[i], sample_size, max_val=1)
    return in_samples

def generate_out_samples(size, sample_size, anomaly_height=0.12):
  
    out_samples = generate_in_samples(size, sample_size)
    
    out_additional_mus = random_generator.uniform(0.1, 0.9, size)
    out_additional_sigmas = random_generator.uniform(0.01, 0.05, size)
    
    for i in range(size):

        anomaly = gen_normal_distribution(
            out_additional_mus[i], 
            out_additional_sigmas[i], 
            sample_size, 
            max_val=anomaly_height
        )
        out_samples[i] += anomaly
    return out_samples

in_samples = generate_in_samples(in_distribution_size, sample_size)
out_samples = generate_out_samples(out_distribution_size, sample_size)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

ax1.plot(np.linspace(0, 1, sample_size), in_samples[42])
ax1.set_title("In-Distribution Sample (Single Peak)")
ax1.set_xlabel("Value")
ax1.set_ylabel("Density")

ax2.plot(np.linspace(0, 1, sample_size), out_samples[42])
ax2.set_title("Out-of-Distribution Sample (Two Peaks)")
ax2.set_xlabel("Value")
ax2.set_ylabel("Density")

plt.tight_layout()
plt.show()

X = np.vstack([in_samples, out_samples])
y = np.hstack([np.ones(in_distribution_size), np.zeros(out_distribution_size)])

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

X_val, X_test, y_val, y_test = train_test_split(
    X_test, y_test, test_size=0.5, random_state=42, stratify=y_test
)

print(f"Train set size: {len(X_train)} (In: {sum(y_train)}, Out: {len(y_train)-sum(y_train)})")
print(f"Validation set size: {len(X_val)} (In: {sum(y_val)}, Out: {len(y_val)-sum(y_val)})")
print(f"Test set size: {len(X_test)} (In: {sum(y_test)}, Out: {len(y_test)-sum(y_test)})")