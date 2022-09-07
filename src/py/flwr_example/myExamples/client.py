import os

import tensorflow as tf
import time
import flwr as fl
import psutil

# Make TensorFlow logs less verbose
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"


# Define Flower client
class CifarClient(fl.client.NumPyClient):
    def __init__(self, model, x_train, y_train, x_test, y_test, RAM_percent, CPU_percent):
        self.model = model
        self.x_train, self.y_train = x_train, y_train
        self.x_test, self.y_test = x_test, y_test
        self.RAM_percent = RAM_percent
        self.CPU_percent = CPU_percent

    def get_properties(self, config):
        receive_time = time.time()
        send_time = config['time']

        # RAM & CPU
        RAM_inv = 100 - self.RAM_percent
        CPU_inv = 100 - self.CPU_percent

        # Delay
        delay = receive_time - send_time
        delay_max = 100
        delay_percent = (delay/delay_max) * 100
        delay_percent_inv = 100 - delay_percent

        # Weights
        computational_weight = {'RAM': 0.2, 'CPU': 1}
        beta= 0
        alpha = 0.9

        # Computational Index
        IC = ((RAM_inv * computational_weight['RAM']) + (CPU_inv * computational_weight['CPU'])) / (computational_weight['CPU'] + computational_weight['RAM'])

        evaluation_index = alpha * IC + (1-alpha) * delay_percent_inv
        print("Evaluation Index: ", evaluation_index)
        return {'RAM': self.RAM_percent, 'CPU': self.CPU_percent, 'delay': delay, 'IE': evaluation_index}

    def get_parameters(self, config):
        """Get parameters of the local model."""
        raise Exception("Not implemented (server-side parameter initialization)")

    def fit(self, parameters, config):
        """Train parameters on the locally held training set."""

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
            validation_split=0.1,
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
        return parameters_prime, num_examples_train, results

    def evaluate(self, parameters, config):
        """Evaluate parameters on the locally held test set."""

        # Update local model with global parameters
        self.model.set_weights(parameters)

        # Get config values
        steps: int = config["val_steps"]

        # Evaluate global model parameters on the local test data and return results
        loss, accuracy = self.model.evaluate(self.x_test, self.y_test, 32, steps=steps)
        num_examples_test = len(self.x_test)
        return loss, num_examples_test, {"accuracy": accuracy}


def main() -> None:

    # Load and compile Keras model
    model = tf.keras.applications.EfficientNetB0(
        input_shape=(32, 32, 3), weights=None, classes=10
    )
    model.compile("adam", "sparse_categorical_crossentropy", metrics=["accuracy"])

    # Load a subset of CIFAR-10 to simulate the local data partition
    (x_train, y_train), (x_test, y_test) = load_partition(0)

    # Used RAM percentage
    RAM_percent = psutil.virtual_memory().percent
    print("RAM Usage: ", RAM_percent, "%")
    # Used CPU percentage
    CPU_percent = psutil.cpu_percent(2)  # for 2 seconds
    print("CPU Usage: ", CPU_percent, "%")

    # Start Flower client
    client = CifarClient(model, x_train, y_train, x_test, y_test, RAM_percent, CPU_percent)

    fl.client.start_numpy_client( server_address="localhost:8080", client=client,)


def load_partition(idx: int):
    """Load 1/10th of the training and test data to simulate a partition."""
    assert idx in range(10)
    (x_train, y_train), (x_test, y_test) = tf.keras.datasets.cifar10.load_data()
    return (
        x_train[idx * 5000 : (idx + 1) * 5000],
        y_train[idx * 5000 : (idx + 1) * 5000],
    ), (
        x_test[idx * 1000 : (idx + 1) * 1000],
        y_test[idx * 1000 : (idx + 1) * 1000],
    )


if __name__ == "__main__":
    main()
