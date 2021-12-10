# -*- coding: utf-8 -*-
"""
Created on Wed Nov 13 14:28:09 2019

@author: bhalb
"""


import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import MinMaxScaler
from scipy import spatial

df = pd.read_csv('data/unicorn-data.csv')
df = df[(df['G'] >= 41) & (df['MP'] >= 10)] # restrict data to players who played at least half the season and 10 MPG
features = df.columns.values[6:] # extract all features to be used later


# function to quickly get the part of a dataframe that matches a certain position, pos_subset(df, 'big', 'Pos')
def pos_subset(df, pos, colname):
    return df[df[colname] == pos]


guards = pos_subset(df, 'guard', 'Pos').loc[:, features].values
wings = pos_subset(df, 'wing', 'Pos').loc[:, features].values
bigs = pos_subset(df, 'big', 'Pos').loc[:, features].values

# standardize each subset for PCA
guards = StandardScaler().fit_transform(guards)
wings = StandardScaler().fit_transform(wings)
bigs = StandardScaler().fit_transform(bigs)

subsets = [pd.DataFrame(guards), pd.DataFrame(wings), pd.DataFrame(bigs)]
result = pd.concat(subsets)

# function to run PCA on each subset and find the n_components for which the explained variance ratio is above 0.9

def pca_subset(max_components, pos_subset, pos_name):
    
    pca_var_list = []
    
    for n_components in range(1, max_components+1):
        pca = PCA(n_components = n_components)
        components = pca.fit_transform(pos_subset)
        pca_variance = sum(pca.explained_variance_ratio_)
        pca_var_list.append(pca_variance)
        #print("For n_components = {} for {}, explained variance ratio is {}".format(n_components, pos_name, pca_variance))
        
    return pca_var_list, [n for n, i in enumerate(pca_var_list) if i > 0.9][0] + 1

pca_var_g, var_index_g = pca_subset(20, subsets[0], 'guards')
pca_var_w, var_index_w = pca_subset(20, subsets[1], 'wings')
pca_var_b, var_index_b = pca_subset(20, subsets[2], 'bigs')

# plot how explained variance ratio changes with n_components among each positional subset

plt.style.use('fivethirtyeight')

pca_fig, ax = plt.subplots()

ax.plot(range(1, 21), pca_var_g, label = 'guards')
ax.plot(range(1, 21), pca_var_w, label = 'wings')
ax.plot(range(1, 21), pca_var_b, label = 'bigs')

ax.set_xlabel('n_components')
ax.set_ylabel('Explained variance ratio')

ax.set_xticks(np.arange(1   , 21, 2.0))
ax.legend(loc = 'best')

pca_fig.suptitle("n_components among positional PCA", weight = 'bold', size = 18)

pca_fig.text(x = -0.05, y = -0.08,
    s = '______________________________________________________________',
    fontsize = 14, color = 'grey', horizontalalignment='left', alpha = .3)

pca_fig.text(x = -0.05, y = -.14,
    s = 'https://dribbleanalytics.blog                     ',
    fontsize = 14, fontname = 'Rockwell', color = 'grey', horizontalalignment='left')

pca_fig.savefig('pca-variance.png', dpi = 400, bbox_inches = 'tight')