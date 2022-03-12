# get data
# y = lineup +/-
# X = summed box score data season averages for each offensive / defensive player

# go through each season
# go through each lineup
# add +/- to y
# get season averages for each player
# add offensive and defensive sums to X

from tensorflow.keras.layers import Conv1D, Dense, Flatten, Input, AvgPool1D, Normalization
from tensorflow import keras
from tensorflow.keras.layers import Layer
import tensorflow as tf
from sklearn.model_selection import train_test_split
import numpy as np
from nba_utils import seasons
from nba import NbaTracker

nbaTracker = NbaTracker()

nbaTracker.load_seasons()

y = np.zeros((0))  # (n_samples)
diff_la = np.zeros((0))
X = []  # (n_samples, 2 * 18 stats)
# (n_samples, 5 players, 18 stats)
offense = np.zeros((0, 5, 18), dtype=np.float32)
# (n_samples, 5 players, 18 stats)
defense = np.zeros((0, 5, 18), dtype=np.float32)
sample_weights = []  # (n_samples)
for season in nbaTracker.seasons.values():
    season.build_player_seasons()

    if not hasattr(season, 'lineups'):
        continue
    season_offense = []
    season_defense = []
    season_ppp = []
    total_points = 0
    total_possessions = 0
    for lineup, stats in season.lineups.items():

        season_ppp.append(stats.shot_points / stats.possessions)
        sample_weights.append(stats.possessions)
        total_points += stats.shot_points
        total_possessions += stats.possessions

        offense_stats = [0] * 18
        offense_player_stats = []
        for offensive_player in lineup.off_players.split('-'):
            pid = int(offensive_player)
            # get per minute stats
            player_stats = season.player_seasons[pid].get_stats()
            for i, stat in enumerate(player_stats):
                offense_stats[i] += stat
            offense_player_stats.append(player_stats)

        defense_stats = [0] * 18
        defense_player_stats = []
        for defensive_player in lineup.def_players.split('-'):
            pid = int(defensive_player)
            # get per minute stats
            player_stats = season.player_seasons[pid].get_stats()
            for i, stat in enumerate(player_stats):
                defense_stats[i] += stat
            defense_player_stats.append(player_stats)

        X.append(offense_stats+defense_stats)
        season_offense.append(offense_player_stats)
        season_defense.append(defense_player_stats)

    season_offense = np.array(season_offense, dtype=np.float32)
    offense = np.concatenate((offense, season_offense), axis=0)
    season_defense = np.array(season_defense, dtype=np.float32)
    defense = np.concatenate((defense, season_defense), axis=0)
    season_ppp = np.array(season_ppp, dtype=np.float32)
    y = np.concatenate((y, season_ppp))
    diff_la = np.concatenate(
        (diff_la, season_ppp - total_points / total_possessions))
    print("loaded", season.name)
X = np.array(X, dtype=np.float32)
# y = np.array(y, dtype=np.float32)
# offense = np.array(offense, dtype=np.float32)
# defense = np.array(defense, dtype=np.float32)
diff_la = np.array(diff_la, dtype=np.float32)
sample_weights = np.array(sample_weights, dtype=np.float32)

X_train, X_test, y_train, y_test, diff_la_train, diff_la_test, offense_train, offense_test, defense_train, defense_test, sample_weights_train, sample_weights_test = train_test_split(
    X, y, diff_la, offense, defense, sample_weights, test_size=0.2, random_state=424)
X_train, X_val, y_train, y_val, diff_la_train, diff_la_val, offense_train, offense_val, defense_train, defense_val, sample_weights_train, sample_weights_val = train_test_split(
    X_train, y_train, diff_la_train, offense_train, defense_train, sample_weights_train, test_size=0.2, random_state=424)


train_dataset = tf.data.Dataset.from_tensor_slices(
    ((offense_train, defense_train), diff_la_train, sample_weights_train))
train_dataset = train_dataset.shuffle(5000).batch(32)
val_dataset = tf.data.Dataset.from_tensor_slices(
    ((offense_val, defense_val), diff_la_val, sample_weights_val))
val_dataset = val_dataset.batch(32)
test_dataset = tf.data.Dataset.from_tensor_slices(
    ((offense_test, defense_test), diff_la_test, sample_weights_test))
test_dataset = test_dataset.batch(32)


class CombineAveBpmLayer(Layer):
    def call(self, X):
        off_ave, def_ave = X
        return tf.multiply(off_ave, 5.) + tf.multiply(def_ave, -5.)

    def compute_output_shape(self, batch_input_shape):
        return (batch_input_shape[1], 1, 1)


off_input = Input(shape=offense.shape[1:])
off_norm = Normalization()(off_input)
off_conv1 = Conv1D(64, 1, activation='relu',
                   kernel_initializer='he_normal')(off_norm)
off_conv2 = Conv1D(64, 1, activation='relu',
                   kernel_initializer='he_normal')(off_conv1)
off_bpm = Conv1D(1, 1)(off_conv2)  # (n, 5, 1)
off_ave = AvgPool1D(pool_size=5)(off_bpm)  # (n, 1, 1)

def_input = Input(shape=defense.shape[1:])
def_norm = Normalization()(def_input)
def_conv1 = Conv1D(64, 1, activation='relu',
                   kernel_initializer='he_normal')(def_norm)
def_conv2 = Conv1D(64, 1, activation='relu',
                   kernel_initializer='he_normal')(def_conv1)
def_bpm = Conv1D(1, 1)(def_conv2)  # (n, 5, 1)
def_ave = AvgPool1D(pool_size=5)(def_bpm)  # (n, 1, 1)

output = CombineAveBpmLayer()([off_ave, def_ave])
output = Flatten()(output)

off_bpm_model = keras.models.Model(inputs=[off_input], outputs=[off_bpm])
def_bpm_model = keras.models.Model(inputs=[def_input], outputs=[def_bpm])
model = keras.models.Model(inputs=[off_input, def_input], outputs=[output])
model.compile(optimizer='adam', loss='mse')
