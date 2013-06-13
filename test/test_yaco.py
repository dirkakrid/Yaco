import os
import tempfile
import unittest
import yaml

import Yaco

test_set_1 = {
    'a' : 1,
    'b' : 2,
    'c' : { 'd' : 3,
            'e' : 4,
            'f' : 5 },
    'g' : [ 0, 1, 2, 3,
           { 'h' : 6,
             'i' : 7,
             'j' : 8 }],
        }

test_set_2 = {
    'a' : 18,
    'b' : { 'k' : 9,
            'm' : 10 },
    'g' : [0, 1, 2, 3, 4, 5]
    }

def d():
    return Yaco.Yaco(test_set_1)

class BasicYacoTest(unittest.TestCase):

    def test_load(self):
        y = Yaco.Yaco()

    def test_simpledict(self):
        y = Yaco.Yaco()
        y['a'] = 1
        y['b'] = 2
        self.assertEqual(y['a'], 1)
        self.assertEqual(y['b'], 2)

        self.assertTrue(y.has_key('b'))
        self.assertTrue('b' in y)

        del(y.b)
        self.assertTrue(not y.has_key('b'))
        self.assertTrue('b' not in y)

    def test_yaco_has_attribute_access(self):
        y = d()
        self.assertEqual(y.a, 1)
        self.assertEqual(y.b, 2)

    def test_yaco_can_do_multiple_levels(self):
        y = Yaco.Yaco()
        y['a'] = Yaco.Yaco()
        y['a']['b'] = 3
        self.assertEqual(y['a']['b'], 3)
        self.assertEqual(y.a.b, 3)

    def test_load_from_dict(self):
        y = Yaco.Yaco(test_set_1)
        self.assertEqual(y['a'], 1)
        self.assertEqual(y.c.e, 4)

    def test_implicit_branch_creation(self):
        y = Yaco.Yaco()
        y.a.b.c = 4
        self.assertEqual(y['a']['b']['c'], 4)
        self.assertEqual(y.a.b.c, 4)

    def test_list_integration(self):
        y = Yaco.Yaco()
        y.a.b.c = 4
        y.a.d = [0,1,2, Yaco.Yaco()]
        y.a.d[3].e = 'test'
        self.assertEqual(y.a.d[3].e, 'test')

    def test_update(self):
        y = Yaco.Yaco(test_set_1)
        self.assertEqual(y.b, 2)
        y.update(test_set_2)
        self.assertNotEqual(y.b, 2)
        self.assertEqual(y.b.m, 10)

    def test_save_and_yaml(self):
        y = Yaco.Yaco(test_set_1)
        tmpfile = tempfile.NamedTemporaryFile(delete=False)
        y.save(tmpfile.name)
        self.assertTrue(os.path.exists(tmpfile.name))
        with open(tmpfile.name) as F:
            YY = yaml.load(F)
        self.assertEqual(YY['a'], 1)
        self.assertEqual(YY['g'][4]['i'], 7)


class BasicPolyYacoTest(unittest.TestCase):

    def setUp(self):
        self.fileA = tempfile.NamedTemporaryFile(delete=False)
        self.fileB = tempfile.NamedTemporaryFile(delete=False)

        self.fileA.close()
        self.fileB.close()

        y = Yaco.Yaco(test_set_1)
        x = Yaco.Yaco(test_set_2)

        y.save(self.fileA.name)
        x.save(self.fileB.name)
        self.files = [['fileA', self.fileA.name],
                      ['fileB', self.fileB.name]]

        self.py = Yaco.PolyYaco(
                'test', base = test_set_1,
                files = self.files)

    def tearDown(self):
        os.remove(self.fileA.name)
        os.remove(self.fileB.name)


    def test_load(self):
        y = Yaco.PolyYaco('test')
        y = Yaco.PolyYaco('test',
                base = test_set_1)
        y = Yaco.PolyYaco('test',
                base = test_set_1,
                files = self.files)

        self.assertTrue(isinstance(y, Yaco.PolyYaco))

        self.assertEqual(y.c.d, 3) # from 2
        self.assertEqual(y.a, 18)  # 2 overrides 1
        self.assertEqual(y.b.k, 9)  # 2 overrides 1

    def test_assignment(self):
        self.assertEqual(self.py.a, 18)
        self.py.a = 19
        self.assertEqual(self.py.a, 19)

    def test_has_key(self):

        self.assertTrue(self.py.has_key('a'))
        self.assertFalse(self.py.has_key('qqq'))

    def test_simple(self):
        smp = self.py.simple()
        self.assertTrue(isinstance(smp, dict))
        self.assertFalse(isinstance(smp, Yaco.Yaco))

    def test_get(self):
        self.assertEqual(self.py.get('a'), 18)
        self.assertEqual(self.py.get('qqq', 77), 77)

    def test_merge(self):
        smp = self.py.merge()
        self.assertTrue(isinstance(smp, dict))
        self.assertTrue(isinstance(smp, Yaco.Yaco))


    def test_save(self):
        y = Yaco.PolyYaco('test',
            base = test_set_1,
            files = self.files)

        yl = Yaco.Yaco()
        yl.load(self.fileB.name)
        self.assertEqual(yl.a, 18)

        self.assertEqual(y.a, 18)
        y.a = 19
        self.assertEqual(y.a, 19)
        y.save()

        yl = Yaco.Yaco()
        yl.load(self.fileB.name)
        self.assertEqual(yl.a, 19)

    def test_edit(self):
        y = Yaco.PolyYaco('test',
                base = test_set_1,
                files = self.files)
