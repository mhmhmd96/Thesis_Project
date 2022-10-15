import math
import os
# Make TensorFlow logs less verbose
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import tensorflow as tf
import flwr as fl
from pythonping import ping
from threading import Thread

ping_count = 1000



# Define Flower client
class CifarClient(fl.client.NumPyClient):
    def __init__(self, model, x_train, y_train, x_test, y_test, delay):
        self.model = model
        self.x_train, self.y_train = x_train, y_train
        self.x_test, self.y_test = x_test, y_test
        #self.available_ram = available_ram
        #self.cpu_percent = cpu_percent
        #self.cpu_count = cpu_count
        self.delay = delay
    def get_properties(self, config):
        print("Delay: ", self.delay)
        #evaluation_index = get_eval_index(self.available_ram, self.cpu_percent, self.cpu_count, self.delay)
        #print("Evaluation Index: ", evaluation_index)
        return {'delay': self.delay}

    def get_parameters(self, config):
        """Get parameters of the local model."""
        raise Exception("Not implemented (server-side parameter initialization)")

    def fit(self, parameters, config):
        """Train parameters on the locally held training set."""
        th = Thread(target=self.ping_host1, args=())
        th.start()
        #print('Delay: ', self.delay)
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

    def ping_host1(self):
        ping_result = ping(target='localhost', count=ping_count, timeout=2)
        #print(ping_result)
        self.delay = ping_result.rtt_avg_ms



def ping_host():
    ping_result = ping(target='localhost', count=40, timeout=2)
    #print(ping_result)
    return ping_result.rtt_avg_ms

def main() -> None:
    delay = ping_host()

    # Load and compile Keras model
    model = tf.keras.applications.mobilenet_v2.MobileNetV2(
    input_shape=(32, 32, 3), weights=None, classes=10)

    model.compile("adam", "sparse_categorical_crossentropy", metrics=["accuracy"])

    # Load a subset of CIFAR-10 to simulate the local data partition
    (x_train, y_train), (x_test, y_test) = load_partition(0)

    # Used RAM percentage
    #available_ram = psutil.virtual_memory().available
    #print("RAM Available: ", available_ram / 1e+9, "GB")
    # Used CPU percentage
    #available_cpu = psutil.cpu_percent(cpu_duration)
    #cpu_count = psutil.cpu_count()
    #print("CPU Usage: ", available_cpu, "%")

    # Start Flower client
    client = CifarClient(model, x_train, y_train, x_test, y_test, delay)

    fl.client.start_numpy_client(server_address="localhost:5555", client=client,)


def load_partition(idx: int):
    """Load 1/10th of the training and test data to simulate a partition."""
    assert idx in range(10)
    train_size = math.floor(50000 / 6)
    test_size = math.floor(10000 / 6)
    (x_train, y_train), (x_test, y_test) = tf.keras.datasets.cifar10.load_data()
    return (
        x_train[idx * train_size : (idx + 1) * train_size],
        y_train[idx * train_size : (idx + 1) * train_size],
    ), (
        x_test[idx * test_size : (idx + 1) * test_size],
        y_test[idx * test_size : (idx + 1) * test_size],
    )



if __name__ == "__main__":
    main()
