import sys
import unittest

import wexpect
from readchar import key


class MyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.sut = wexpect.spawn("../venv/Scripts/python.exe ../vpc_cli/main.py")
        self.sut.expect("test.*", timeout=1)

    def test_something(self):
        self.sut.send(key.DOWN)
        self.sut.expect("test*", timeout=1)


if __name__ == '__main__':
    # unittest.main()

    # sut = wexpect.spawn("../venv/Scripts/python.exe ../vpc_cli/main.py")
    child = wexpect.spawn('cmd.exe')
    child.expect('>')
    child.sendline('ls')
    child.expect('>')
    print(child.before)
    child.sendline('exit')
