# from urllib import request

import cv2
import numpy as np
import random
import os


def hash_it(string):
    """
    Make hash of a string
    """
    p = 127
    Hash = 0
    for elem in string:
        Hash = Hash * p + ord(elem)
    return Hash


def pystate_to_npstate(pystate):
    """
    Convert state of a Python Random object to state usable
    by NumPy RandomState.
    """
    version, (*keys, pos), cached_gaussian = pystate
    NP_VERSION = 'MT19937'
    has_gauss = cached_gaussian is not None
    npstate = (
        NP_VERSION,
        keys,
        pos,
        has_gauss,
        cached_gaussian if has_gauss else 0.0
    )
    return npstate


def np_rand_seed(string):
    """
    :param string: string to be seeded in numpay.random
    :return: numpay.random
    """
    np_rand = np.random.RandomState(seed=0)
    py_rand = random.Random(hash_it(string))
    np_rand.set_state(pystate_to_npstate(py_rand.getstate()))
    return np_rand


def gen_key(shape, rand):
    """
    :param shape: image size
    :param rand: numpay.random.Randomstate()
    :return: key
    """
    return rand.randint(0, 256, size=shape, dtype=np.uint8)


def xor(image, pas):
    rand = np_rand_seed(pas)
    key = gen_key(image.shape, rand)
    return cv2.bitwise_xor(image, key)


if __name__ == "__main__":
    # img = cv2.imread("images/test.jpg")
    #
    # url = "https://api.telegram.org/file/{TOKEN}/photos/file_25.jpg"
    # url_response = request.urlopen(url)
    # img_array = np.array(bytearray(url_response.read()), dtype=np.uint8)
    # img = cv2.imdecode(img_array, -1)
    #
    # password = input("Enter password: ")
    # rand = np_rand_seed(password)
    # key = gen_key(img.shape, rand)
    # encryption = xor(img, key)
    # decryption = xor(encryption, key)
    # cv2.imshow("decryption", decryption)
    # cv2.waitKey()
    # cv2.destroyAllWindows()
    #
    # while password != "":
    #
    #     password = input("Enter password: ")
    #     rand = np_rand_seed(password)
    #     key = gen_key(img.shape, rand)
    #     decryption = xor(encryption, key)
    #     cv2.imshow("decryption", decryption)
    #     cv2.waitKey()
    #     cv2.destroyAllWindows()

    while True:
        print('Choose operation:\n[1 - encrypt]\n[2 - decrypt]')
        op = input()
        if op == '1':
            path = input('Enter path to the image to encrypt: ').replace('''"''', '')
            while not os.path.exists(path):
                print(f"Sorry {path=} don't exists")
                path = input('Enter path to the image to encrypt: ').replace('''"''', '')
            img = cv2.imread(path)
            password = input("Enter password: ")
            encryption = xor(img, password)
            cv2.imwrite(path[:path.rfind('.')]+'_enc.png', encryption)
            print(f"Encrypted image was successfully saved in path: {path[:path.rfind('.')]+'_enc.png'}")
        elif op == '2':
            path = input('Enter path to the image to decrypt: ').replace('''"''', '')
            while not os.path.exists(path):
                print(f"Sorry {path=} don't exists")
                path = input('Enter path to the image to decrypt: ').replace('''"''', '')
            img = cv2.imread(path)
            password = input("Enter password: ")
            decryption = xor(img, password)
            cv2.imwrite(path[:path.rfind('.')]+'_dec.png', decryption)
            print(f"Decrypted image was successfully saved in path: {path[:path.rfind('.')]+'_dec.png'}")
        else:
            print('''Please enter "1" or "2" value''')
