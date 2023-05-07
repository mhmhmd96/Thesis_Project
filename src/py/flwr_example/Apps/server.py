import logging
from typing import Dict, Optional, Tuple
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

from keras.layers import Dense
from keras import Model
from keras.optimizers import Adamax
import flwr as fl
import tensorflow as tf

use_selection_strategy = True
def get_dense169_model():
    conv = tf.keras.applications.DenseNet169(weights='imagenet', include_top=False,
                                             input_shape=(32, 32, 3), pooling='max', )
    conv.trainable = True
    model = tf.keras.models.Sequential([
        conv,
        Dense(units=10, activation="softmax")
    ])
    model.compile(optimizer=Adamax(learning_rate=0.01), loss='categorical_crossentropy', metrics=['accuracy'])
    # model.summary()
    return model

def get_dense_model():
    conv = tf.keras.applications.DenseNet121(weights='imagenet', include_top=False,
                                       input_shape=(32, 32, 3), pooling='max',
                                       )
    conv.trainable = True
    model = tf.keras.models.Sequential([
        conv,
        # Dense(units=128, activation="relu"),
        # Dense(units=64, activation="relu"),
        Dense(units=10, activation="softmax")
    ])
    model.compile(optimizer=Adamax(learning_rate=0.0003), loss='categorical_crossentropy', metrics=['accuracy'])
    #model.summary()
    return model
def get_mobile_model():
    mobile = tf.keras.applications.mobilenet.MobileNet(include_top=False,
                                                               input_shape=(32,32,3),
                                                               pooling='max', weights='imagenet',
                                                               alpha=1, depth_multiplier=1,dropout=.4)
    x=mobile.layers[-1].output
    x=tf.keras.layers.BatchNormalization(axis=-1, momentum=0.99, epsilon=0.001)(x)
    predictions=Dense(10, activation='softmax')(x)
    model = Model(inputs=mobile.input, outputs=predictions)
    for layer in model.layers:
        layer.trainable = True
    model.compile(Adamax(learning_rate=0.001), loss='categorical_crossentropy', metrics=['accuracy'])
    return model

def main() -> None:
    # Load and compile model for
    # 1. server-side parameter initialization
    # 2. server-side parameter evaluation
    model = get_dense_model()
    #model = get_dense169_model()

    # Create strategy
    strategy = fl.server.strategy.FedAvg(
        selection_strategy=use_selection_strategy,
        fraction_fit=0.75,
        fraction_evaluate=0.5,
        min_fit_clients=1,
        min_evaluate_clients=1,
        min_available_clients=1,
        evaluate_fn=get_evaluate_fn(model),
        on_fit_config_fn=fit_config,
        on_evaluate_config_fn=evaluate_config,
        initial_parameters=fl.common.ndarrays_to_parameters(model.get_weights()),
    )

    # Start Flower server (SSL-enabled) for four rounds of federated learning
    fl.server.start_server(
        server_address="192.168.122.178:5555",
        config=fl.server.ServerConfig(num_rounds=25,),
        strategy=strategy,
    )


def get_evaluate_fn(model):
    """Return an evaluation function for server-side evaluation."""

    (x_train, y_train), _ = tf.keras.datasets.cifar10.load_data()
    y_train = tf.keras.utils.to_categorical(y_train, 10)
    #x_train = vgg16.preprocess_input(x_train)
    x_train = x_train.astype('float32')
    x_train /= 255

    x_val, y_val = x_train[45000:50000], y_train[45000:50000]

    # The `evaluate` function will be called after every round
    def evaluate(
        server_round: int,
        parameters: fl.common.NDArrays,
        config: Dict[str, fl.common.Scalar],
    ) -> Optional[Tuple[float, Dict[str, fl.common.Scalar]]]:
        model.set_weights(parameters)  # Update model with the latest parameters
        loss, accuracy = model.evaluate(x_val, y_val)
        return loss, {"accuracy": accuracy}

    return evaluate


def fit_config(server_round: int):
    """Return training configuration dict for each round.

    Keep batch size fixed at 32, perform two rounds of training with one
    local epoch, increase to two local epochs afterwards.
    """
    config = {
        "batch_size": 128,
        "round_num": server_round,
        "local_epochs": 1, #if server_round < 2 else 2,
    }
    return config


def evaluate_config(server_round: int):
    """Return evaluation configuration dict for each round.

    Perform five local evaluation steps on each client (i.e., use five
    batches) during rounds one to three, then increase to ten local
    evaluation steps.
    """
    val_steps = 20 #if server_round < 4 else 10
    return {"val_steps": val_steps, "round_num": server_round,}


if __name__ == "__main__":

    main()
