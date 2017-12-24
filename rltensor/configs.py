import tensorflow as tf

from rltensor.processors import AtariProcessor
from rltensor.networks import Categorical


scale = 10000


def agent_config():
    _agent_config = dict(
        optimizer_spec={"type": "rmsp", "momentum": 0.95, "epsilon": 0.01},
        lr_spec={"lr_init": 2.5e-4, "lr_decay_step": 5 * scale,
                 "lr_decay": 0.96, "lr_min": 2.5e-4},
        t_learn_start=5 * scale,
        t_update_freq=4,
        tensorboard_dir="./logs"
    )
    return _agent_config


def dqn_config():
    _dqn_config = dict(
        ciritc_cls=Categorical,
        critic_spec=[
                {"name": "conv2d", "kernel_size":(8, 8), "num_filters":32, "stride":4,
                 "padding": 'SAME', "is_batch":False, 'activation': tf.nn.relu},
             {"name": "conv2d", "kernel_size":(4, 4), "num_filters":64, "stride":2,
             "padding": 'SAME', "is_batch":False, 'activation': tf.nn.relu},
             {"name": "conv2d", "kernel_size": (3, 3), "num_filters":64, "stride":1,
             "padding": 'SAME', "is_batch":False, 'activation': tf.nn.relu},
                {"name": "dense", "is_flatten":True, "is_batch":False, "num_units": 512, 'activation': tf.nn.relu},
        ],
        processor=AtariProcessor(84, 84),
        explore_spec={"t_ep_end": 100 * scale, "ep_start": 1.0, "ep_end": 0.1},
        memory_limit=100 * scale,
        window_length=4,
        is_prioritized=False,
        batch_size=32,
        error_clip=1.0,
        discount=0.99,
        t_target_q_update_freq=1 * scale,
        double_q=True,
    )
    _dqn_config.update(agent_config())
    return _dqn_config


def fit_config():
    _fit_config = dict(
        t_max=5000 * scale,
        num_max_start_steps=30,
        log_freq=int(scale * 0.1) + 1
    )
    return _fit_config