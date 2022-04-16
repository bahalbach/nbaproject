from genericpath import isdir


import tensorflow as tf
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, LabelBinarizer, OrdinalEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
import pandas as pd
from nba_dataclasses import EventType, ResultClass
from sklearn.model_selection import train_test_split
from nba import NbaTracker

columns = ['result_class', 'result_team', 'num_fts', 'shot_type',
           'is_blocked', 'is_putback', 'in_penalty', 'offense_is_home', 'score_margin']
non_player_columns = columns[:]
num_rebound_inputs = 6

catagorical_attributes = ['shot_type']
binary_attributes = ['is_blocked', 'is_putback',
                     'in_penalty', 'offense_is_home']
numerical_attributes = ['score_margin']


def get_rebound_df_from_games(games):
    rebounds = []
    for game in games:
        last_game_event = None
        for ge in game.game_events:
            if ge.event_type == EventType.Rebound:
                result_class = ge.result.result_class
                # if result_class == ResultClass.JUMPBALL:
                #     result_team = 2
                if result_class in {
                        ResultClass.OFF_REBOUND, ResultClass.FT, ResultClass.SAME_TEAM}:
                    result_team = 1
                else:
                    result_team = 0
                num_fts = ge.result.num_fts
                shot_type = ge.result.shot_type
                is_blocked = ge.result.is_blocked
                is_putback = last_game_event.is_putback
                in_penalty = ge.in_penalty
                offense_is_home = ge.offense_is_home
                score_margin = ge.score_margin

                rebound = [
                    result_class,
                    result_team,
                    num_fts,
                    shot_type,
                    is_blocked,
                    is_putback,
                    in_penalty,
                    offense_is_home,
                    score_margin,
                ]

                rebounds.append(rebound)
            last_game_event = ge
    return pd.DataFrame(rebounds, columns=columns)


def build_simple_rebound_model(season, random_state=432536):
    games = season.games

    train_games, test_games = train_test_split(
        list(games.values()), test_size=0.1, random_state=432536)

    train_rebounds = get_rebound_df_from_games(train_games)
    test_rebounds = get_rebound_df_from_games(test_games)

    train_X = train_rebounds.drop(
        ['result_class', 'result_team', 'num_fts'], axis=1)
    train_y = train_rebounds['result_class']
    train_is_oreb = train_rebounds['result_team']
    test_X = test_rebounds.drop(
        ['result_class', 'result_team', 'num_fts'], axis=1)
    test_y = test_rebounds['result_class']
    test_is_oreb = test_rebounds['result_team']

    # transform catagorical attributes to one-hot encoding
    preprocess = ColumnTransformer([("categorical", OneHotEncoder(), catagorical_attributes), (
        "binary", 'passthrough', binary_attributes), ("numerical", StandardScaler(), numerical_attributes)])

    processed_train_X = tf.cast(
        preprocess.fit_transform(train_X), dtype=tf.float32)
    processed_test_X = tf.cast(
        preprocess.transform(test_X), dtype=tf.float32)

    path = f'saved_model/rebound_model{season.name}'
    if isdir(path):
        rebound_model = tf.keras.models.load_model(path)
    else:
        processed_train_y = train_y.to_numpy().reshape(-1, 1) - 1
        processed_test_y = test_y.to_numpy().reshape(-1, 1) - 1

        train_dataset = tf.data.Dataset.from_tensor_slices(
            (processed_train_X, (processed_train_y, train_is_oreb.to_numpy().reshape(-1, 1)))).shuffle(10000).batch(32).prefetch(1)
        test_dataset = tf.data.Dataset.from_tensor_slices(
            (processed_test_X, (processed_test_y, test_is_oreb.to_numpy().reshape(-1, 1)))).shuffle(10000).batch(32).prefetch(1)

        inputs = tf.keras.Input(processed_train_X.shape[1:])
        rebound_type = tf.keras.layers.Dense(10, activation='softmax')(inputs)
        is_oreb = tf.keras.layers.Dense(1, activation='sigmoid')(inputs)

        rebound_model = tf.keras.Model(
            inputs=inputs, outputs=[rebound_type, is_oreb])
        loss_fn = tf.keras.losses.SparseCategoricalCrossentropy(
            from_logits=False)
        rebound_model.compile(
            optimizer='adam',
            loss=[loss_fn, 'binary_crossentropy'],
            metrics=['accuracy'])

        print("built model, now training")
        # fit data
        history = rebound_model.fit(train_dataset, epochs=1)
        rebound_model.save(path)

    return preprocess, rebound_model
    # def stack_dict(inputs, fun=tf.stack):
    #     values = []
    #     for key in sorted(inputs.keys()):
    #         values.append(tf.cast(inputs[key], tf.float32))

    #     return fun(values, axis=-1)
    # inputs = {}
    # for name, column in train_X.items():
    #     if (name in catagorical_attributes or name in binary_attributes):
    #         dtype = tf.int64
    #     else:
    #         dtype = tf.float32
    #     inputs[name] = tf.keras.Input(shape=(), name=name, dtype=dtype)

    # processed = []
    # for name in binary_attributes:
    #     inp = inputs[name]
    #     inp = inp

    # rebound_model.evaluate(processed_test_X, [
    #                     test_y-1, test_is_oreb.to_numpy().reshape(-1, 1)], verbose=2)
