import os


def google_key():
    key_parts_tuple = ('-----BEGIN PRIVATE KEY-----', os.environ['PRIVATE_KEY_1'], os.environ['PRIVATE_KEY_2'],
                           os.environ['PRIVATE_KEY_3'],
                           os.environ['PRIVATE_KEY_4'], os.environ['PRIVATE_KEY_5'], os.environ['PRIVATE_KEY_6'],
                           os.environ['PRIVATE_KEY_7'], os.environ['PRIVATE_KEY_8'], os.environ['PRIVATE_KEY_9'],
                           os.environ['PRIVATE_KEY_10'], os.environ['PRIVATE_KEY_11'], os.environ['PRIVATE_KEY_12'],
                           os.environ['PRIVATE_KEY_13'], os.environ['PRIVATE_KEY_14'], os.environ['PRIVATE_KEY_15'],
                           os.environ['PRIVATE_KEY_16'], os.environ['PRIVATE_KEY_17'], os.environ['PRIVATE_KEY_18'],
                           os.environ['PRIVATE_KEY_19'], os.environ['PRIVATE_KEY_20'], os.environ['PRIVATE_KEY_21'],
                           os.environ['PRIVATE_KEY_22'], os.environ['PRIVATE_KEY_23'], os.environ['PRIVATE_KEY_24'],
                           os.environ['PRIVATE_KEY_25'], os.environ['PRIVATE_KEY_26'], '-----END PRIVATE KEY-----')

    key_ = ''

    for part in key_parts_tuple:
        key_ += part
        key_ += '\n'

    return key_