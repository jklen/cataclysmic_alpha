
#%% packages
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
# Create a sample DataFrame

#%% data

data = {
    'A': np.random.rand(10),
    'B': np.random.rand(10),
    'C': np.random.rand(10)
}
df = pd.DataFrame(data)

# Display the DataFrame
print(df)
#%%
# Plotting
plot = df.plot(title='Random Data', figsize=(10, 6))

# Adding labels
plot.set_xlabel('Index')
plot.set_ylabel('Values')

# Show plot
plot.legend(title='Legend')
plt.show()

#TODO test
# %%
