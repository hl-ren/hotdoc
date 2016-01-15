import os, sys

from collections import defaultdict

from hotdoc.utils.utils import get_mtime, OrderedSet

class ChangeTracker(object):
    def __init__(self):
        self.exts_mtimes = {}
        self.hard_deps_mtimes = {}
        self.mtimes = defaultdict(defaultdict)

    def get_stale_files(self, all_files, fileset_name):
        stale = OrderedSet()

        previous_mtimes = self.mtimes[fileset_name]
        new_mtimes = defaultdict()

        for filename in all_files:
            mtime = get_mtime(filename)
            prev_mtime = previous_mtimes.pop(filename, None)
            new_mtimes[filename] = mtime
            if mtime == prev_mtime:
                continue

            stale.add(filename)

        self.mtimes[fileset_name] = new_mtimes
        return stale, set(previous_mtimes.keys())

    def __track_code_changes(self):
        modules = [m.__file__ for m in sys.modules.values()
                        if m and '__file__' in m.__dict__]

        for filename in modules:
            if filename.endswith('.pyc') or filename.endswith('.pyo'):
                filename = filename[:-1]

            self.add_hard_dependency(filename)

    def track_core_dependencies(self):
        self.__track_code_changes()

    def add_hard_dependency(self, filename):
        mtime = get_mtime(filename)

        if mtime != -1:
            self.hard_deps_mtimes[filename] = mtime

    def hard_dependencies_are_stale(self):
        _win32 = (sys.platform == 'win32')

        for filename, last_mtime in self.hard_deps_mtimes.items():
            mtime = get_mtime(filename)

            if mtime == -1 or mtime != last_mtime:
                return True

        return False

if __name__=='__main__':
    ct = ChangeTracker()

    # Initial build
    os.system('touch a b c d')
    print ("Should be ([a, b, c, d], [])")
    print (ct.get_stale_files(['a', 'b', 'c', 'd'], 'testing'))

    # Build where nothing changed
    print ("Should be ([], [])")
    print (ct.get_stale_files(['a', 'b', 'c', 'd'], 'testing'))

    # Build with two files changed
    os.system('touch b d')
    print ("Should be ([b, d], [])")
    print (ct.get_stale_files(['a', 'b', 'c', 'd'], 'testing'))

    # Build where one file was removed
    os.system('rm -f b')
    print ("Should be ([b], [])")
    print (ct.get_stale_files(['a', 'b', 'c', 'd'], 'testing'))
    print ("Should be ([], [])")
    print (ct.get_stale_files(['a', 'b', 'c', 'd'], 'testing'))

    # Build where one file was unlisted
    print ("Should be ([], [a])")
    print (ct.get_stale_files(['b', 'c', 'd'], 'testing'))

    # Build with file listed again
    print ("Should be ([a], [])")
    print (ct.get_stale_files(['a', 'b', 'c', 'd'], 'testing'))

    os.system('rm -f a b c d')