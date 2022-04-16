from nba import NbaTracker
from nba_api.stats.static.players import find_player_by_id
from nba_api.stats.static.teams import find_team_name_by_id
from genericpath import isdir
import tensorflow as tf
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder, LabelBinarizer, OrdinalEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
import pandas as pd
import numpy as np
from nba_dataclasses import EventType, ResultClass
from sklearn.model_selection import train_test_split
from nba_dataclasses import PossessionTry


y1_columns = ['result_class']
y2_columns = ['shot_type']
y3_columns = ['points', 'off_fts', 'def_fts']

X_columns = ['start_type', 'period', 'period_time_left',
             'in_penalty', 'offense_is_home', 'score_margin', 'is_garbage_time']

catagorical_attributes = ['start_type']
binary_attributes = ['in_penalty', 'offense_is_home', 'is_garbage_time']
numerical_attributes = ['period', 'period_time_left', 'score_margin']


def get_try_df_from_games(games):
    tries = []
    for game in games:
        for ge in game.game_events:
            if ge.event_type == EventType.PossessionTry:
                result: PossessionTry = ge.result

                shot_type = result.shot_type
                if shot_type is None:
                    shot_type = 0

                possession_try = [
                    result.result_class,
                    shot_type,
                    result.points,
                    result.off_fts,
                    result.def_fts,

                    result.try_start.start_type.value,
                    ge.period,
                    result.try_start.period_time_left,
                    ge.in_penalty,
                    ge.offense_is_home,
                    ge.score_margin,
                    ge.is_garbage_time,
                ]

                tries.append(possession_try)
    return pd.DataFrame(tries, columns=y1_columns+y2_columns+y3_columns+X_columns)


def build_simple_try_model(season, random_state=432536):
    games = season.games

    train_games, test_games = train_test_split(
        list(games.values()), test_size=0.1, random_state=432536)

    train_tries = get_try_df_from_games(train_games)
    train_y = (train_tries[y1_columns].to_numpy() - 1,
               train_tries[y2_columns].to_numpy(),
               train_tries[y3_columns].to_numpy())
    train_X = train_tries[X_columns]

    test_tries = get_try_df_from_games(test_games)
    test_y = (test_tries[y1_columns].to_numpy() - 1,
              test_tries[y2_columns].to_numpy(),
              test_tries[y3_columns].to_numpy())
    test_X = test_tries[X_columns]

    # transform catagorical attributes to one-hot encoding
    preprocess = ColumnTransformer([("categorical", OneHotEncoder(), catagorical_attributes), (
        "binary", 'passthrough', binary_attributes), ("numerical", StandardScaler(), numerical_attributes)])

    processed_train_X = tf.cast(
        preprocess.fit_transform(train_X), dtype=tf.float32)
    processed_test_X = tf.cast(
        preprocess.transform(test_X), dtype=tf.float32)

    path = f'saved_model/possession_try_model{season.name}'

    if isdir(path):
        try_model2 = tf.keras.models.load_model(path)
    else:
        train_dataset = tf.data.Dataset.from_tensor_slices(
            (processed_train_X, train_y))
        train_dataset = train_dataset.shuffle(10000).batch(32).prefetch(1)

        # build more complicated version of model

        dense1 = tf.keras.layers.Dense(32, activation='relu')(inputs)
        dense2 = tf.keras.layers.Dense(32, activation='relu')(dense1)
        try_result_class2 = tf.keras.layers.Dense(
            10, activation='softmax')(dense2)
        try_shot_type2 = tf.keras.layers.Dense(6, activation='softmax')(dense2)
        try_num_values2 = tf.keras.layers.Dense(
            3, activation='softmax')(dense2)

        try_model2 = tf.keras.Model(
            inputs=inputs,
            outputs=[try_result_class2, try_shot_type2, try_num_values2]
        )

        try_model2.compile(
            optimizer='adam',
            loss=['sparse_categorical_crossentropy',
                  'sparse_categorical_crossentropy',
                  'mse'],
        )

        history = try_model2.fit(train_dataset, epochs=5)
        try_model2.save(path)

    return preprocess, try_model2
