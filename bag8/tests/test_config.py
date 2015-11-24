from bag8.config import Config


def test_iter_data_paths():

    config = Config()

    # remove all configured paths but add a working one
    config._data_paths = ['data']
    assert set([path for path, project in config.iter_data_paths()]) == set([
        'data',
    ])

    config = Config()

    # remove all configured paths and add non existing one
    config._data_paths = ['dummy']
    # should not return valid path/project tuple
    assert not [path for path, project in config.iter_data_paths()]
