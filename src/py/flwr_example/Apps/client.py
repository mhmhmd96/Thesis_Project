import os

# Make TensorFlow logs less verbose
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import tensorflow as tf
from tensorflow.keras.applications import vgg16
from tensorflow.keras.layers import Flatten, Dense, Dropout
from tensorflow.keras import Model
from tensorflow.keras.optimizers import Adamax
import flwr as fl
from pythonping import ping
from threading import Thread
import time

ping_count = 2000


def get_vgg_model():
    conv = tf.keras.applications.DenseNet121(weights='imagenet', include_top=False,
                                             input_shape=(32, 32, 3), pooling='max', )
    conv.trainable = True
    model = tf.keras.models.Sequential([
        conv,
        Dense(units=10, activation="softmax")
    ])
    model.compile(optimizer=Adamax(), loss='categorical_crossentropy', metrics=['accuracy'])
    # model.summary()
    return model


def get_mobile_model():
    mobile = tf.keras.applications.MobileNet(include_top=False,
                                             input_shape=(32, 32, 3),
                                             pooling='max', weights='imagenet',
                                             alpha=1, depth_multiplier=1, dropout=.4)
    x = mobile.layers[-1].output
    x = tf.keras.layers.BatchNormalization(axis=-1, momentum=0.99, epsilon=0.001)(x)
    predictions = Dense(10, activation='softmax')(x)
    model = Model(inputs=mobile.input, outputs=predictions)
    for layer in model.layers:
        layer.trainable = True
    model.compile(Adamax(learning_rate=0.001), loss='categorical_crossentropy', metrics=['accuracy'])
    return model


# Define Flower client
class CifarClient(fl.client.NumPyClient):
    def __init__(self, model, x_train, y_train, x_test, y_test, delay=0, flag=True):
        self.model = model
        self.x_train, self.y_train = x_train, y_train
        self.x_test, self.y_test = x_test, y_test
        # self.available_ram = available_ram
        # self.cpu_percent = cpu_percent
        # self.cpu_count = cpu_count
        self.delay = delay
        self.flag = flag

    def get_properties(self, config):
        print("Delay: ", self.delay)

        # evaluation_index = get_eval_index(self.available_ram, self.cpu_percent, self.cpu_count, self.delay)
        # print("Evaluation Index: ", evaluation_index)
        return {'delay': self.delay}

    def get_parameters(self, config):
        """Get parameters of the local model."""
        raise Exception("Not implemented (server-side parameter initialization)")

    def fit(self, parameters, config):
        """Train parameters on the locally held training set."""
        # th = Thread(target=self.ping_host1, args=())
        # th.start()
        # print('Delay: ', self.delay)
        # Update local model parameters
        self.model.set_weights(parameters)

        # Get hyperparameters for this round
        batch_size: int = config["batch_size"]
        epochs: int = config["local_epochs"]

        # Train the model using hyperparameters from config
        history = self.model.fit(
            self.x_train,
            self.y_train,
            batch_size,
            epochs,
            validation_split=0.2,
        )

        # Return updated model parameters and results
        parameters_prime = self.model.get_weights()
        num_examples_train = len(self.x_train)
        results = {
            "loss": history.history["loss"][0],
            "accuracy": history.history["accuracy"][0],
            "val_loss": history.history["val_loss"][0],
            "val_accuracy": history.history["val_accuracy"][0],
        }
        th = Thread(target=self.ping_host1, args=())
        th.start()
        self.flag = False
        return parameters_prime, num_examples_train, results

    def evaluate(self, parameters, config):
        """Evaluate parameters on the locally held test set."""

        # Update local model with global parameters
        self.model.set_weights(parameters)

        # Get config values
        steps: int = config["val_steps"]

        # Evaluate global model parameters on the local test data and return results
        loss, accuracy = self.model.evaluate(self.x_test, self.y_test, 32, steps=steps)
        if self.flag:
            th = Thread(target=self.ping_host1, args=())
            th.start()
        num_examples_test = len(self.x_test)
        return loss, num_examples_test, {"accuracy": accuracy}

    def ping_host1(self):
        s = time.time()
        ping_result = ping(target='192.168.122.107', count=ping_count, timeout=5)
        r = time.time()
        delay = r - s
        self.delay = delay


def ping_host():
    s = time.time()
    ping_result = ping(target='192.168.122.107', count=ping_count, timeout=5)
    r = time.time()
    delay = r - s
    return delay


def main() -> None:
    delay = ping_host()

    # Load and compile Keras model
    model = get_vgg_model()

    # Load a subset of CIFAR-10 to simulate the local data partition
    (x_train, y_train), (x_test, y_test) = load_partition(5)

    # Start Flower client
    client = CifarClient(model, x_train, y_train, x_test, y_test, delay)

    fl.client.start_numpy_client(server_address="192.168.122.107:5555", client=client, )


def load_partition(idx: int):
    """Load 1/10th of the training and test data to simulate a partition."""
    assert idx in range(10)
    (x_train, y_train), (x_test, y_test) = tf.keras.datasets.cifar10.load_data()
    x_train, y_train = x_train[idx * 5000: (idx + 1) * 5000], y_train[idx * 5000: (idx + 1) * 5000]
    x_test, y_test = x_test[idx * 1000: (idx + 1) * 1000], y_test[idx * 1000: (idx + 1) * 1000]
    y_train = tf.keras.utils.to_categorical(y_train, 10)
    y_test = tf.keras.utils.to_categorical(y_test, 10)
    # x_train = vgg16.preprocess_input(x_train)
    # x_test = vgg16.preprocess_input(x_test)
    x_train = x_train.astype('float32')
    x_test = x_test.astype('float32')
    x_train /= 255
    x_test /= 255

    return (
               x_train, y_train,
           ), (
               x_test, y_test,
           )


if __name__ == "__main__":
    main()
