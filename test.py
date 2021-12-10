# -*- coding: utf-8 -*-
"""
Created on Wed Nov 13 13:55:20 2019

@author: bhalb
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_style("darkgrid")

fig, ax1 = plt.subplots(1,1)
ax2 = ax1.twinx()

x1 = np.linspace(0, 4 * np.pi, 100)
y1 = np.sin(x1)
function1 = ax1.plot(x1, y1, 'b', label='Sine')

x2 = np.linspace(0, 4 * np.pi, 100)
y2 = np.cos(x2)
function2 = ax2.plot(x2, y2, 'r', label='Cosine')

functions = function1 + function2
labels = [f.get_label() for f in functions]
plt.legend(functions, labels, loc=0)

ax1.set_xlabel('$x$')
ax1.set_ylabel('$y_1$')
ax2.set_ylabel('$y_2$')

plt.title('Sine and Cosine')

plt.tight_layout()

plt.savefig('sin_cos6.png')