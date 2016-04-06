# -*- coding: utf-8 -*-
#
# Copyright © 2016 Mathieu Duponchelle <mathieu.duponchelle@opencreed.com>
# Copyright © 2016 Collabora Ltd
#
# This library is free software; you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# This library is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this library.  If not, see <http://www.gnu.org/licenses/>.

# pylint: disable=missing-docstring
# pylint: disable=invalid-name
# pylint: disable=no-self-use
# pylint: disable=too-few-public-methods

import unittest
import shutil
import io
import os

from hotdoc.core.doc_database import DocDatabase
from hotdoc.core.links import LinkResolver
from hotdoc.parsers import cmark
from hotdoc.parsers.standalone_parser import (
    SitemapParser, SitemapDuplicateError,
    SitemapError)
from hotdoc.utils.utils import IndentError
from hotdoc.utils.loggable import Logger


class TestSitemapParser(unittest.TestCase):

    def setUp(self):
        here = os.path.dirname(__file__)
        self.__tmp_dir = os.path.abspath(os.path.join(
            here, 'sitemap-test'))
        shutil.rmtree(self.__tmp_dir, ignore_errors=True)
        os.mkdir(self.__tmp_dir)
        self.parser = SitemapParser()
        Logger.silent = True

    def tearDown(self):
        shutil.rmtree(self.__tmp_dir, ignore_errors=True)

    def parse(self, text):
        path = os.path.join(self.__tmp_dir, 'sitemap.txt')
        with io.open(path, 'w', encoding='utf-8') as _:
            _.write(text)
        return self.parser.parse(path)

    def test_basic(self):
        inp = (u'index.markdown\n'
               '\tsection.markdown')
        sitemap = self.parse(inp)
        all_sources = sitemap.get_all_sources()
        self.assertEqual(len(all_sources), 2)
        self.assertEqual(all_sources['index.markdown'],
                         ['section.markdown'])

    def test_nesting(self):
        inp = (u'index.markdown\n'
               '\tsection.markdown\n'
               '\t\tsubsection.markdown')

        sitemap = self.parse(inp)
        all_sources = sitemap.get_all_sources()
        self.assertEqual(len(all_sources), 3)
        self.assertEqual(all_sources['index.markdown'],
                         ['section.markdown'])
        self.assertEqual(all_sources['section.markdown'],
                         ['subsection.markdown'])

    def test_unnesting(self):
        inp = (u'index.markdown\n'
               '\tsection1.markdown\n'
               '\t\tsubsection.markdown\n'
               '\tsection2.markdown')

        sitemap = self.parse(inp)
        all_sources = sitemap.get_all_sources()
        self.assertEqual(len(all_sources), 4)
        self.assertEqual(all_sources['index.markdown'],
                         ['section1.markdown', 'section2.markdown'])

    def test_empty_lines(self):
        inp = (u'index.markdown\n'
               '\n'
               '\tsection.markdown')
        sitemap = self.parse(inp)
        all_sources = sitemap.get_all_sources()
        self.assertEqual(len(all_sources), 2)
        self.assertEqual(all_sources['index.markdown'],
                         ['section.markdown'])

    def test_quoting(self):
        inp = (u'index.markdown\n'
               '\t" section with spaces.markdown "')
        sitemap = self.parse(inp)
        all_sources = sitemap.get_all_sources()
        self.assertEqual(len(all_sources), 2)
        self.assertEqual(all_sources['index.markdown'],
                         [' section with spaces.markdown '])

    def test_invalid_indentation(self):
        inp = (u'index.markdown\n'
               '\tsection1.markdown\n'
               '\tsection2.markdown\n'
               '\t invalid.markdown\n'
               '\tsection3.markdown\n'
               '\tsection4.markdown\n'
               '\tsection5.markdown')
        with self.assertRaises(IndentError) as cm:
            self.parse(inp)
        self.assertEqual(cm.exception.lineno, 3)
        self.assertEqual(cm.exception.column, 9)
        self.assertEqual(cm.exception.filename,
                         os.path.join(self.__tmp_dir, 'sitemap.txt'))

    def test_duplicate_file(self):
        inp = (u'index.markdown\n'
               '\tsection.markdown\n'
               '\tsection.markdown\n')

        with self.assertRaises(SitemapDuplicateError) as cm:
            self.parse(inp)
        self.assertEqual(cm.exception.lineno, 2)
        self.assertEqual(cm.exception.column, 9)

    def test_multiple_roots(self):
        inp = (u'index.markdown\n'
               'other_index.markdown\n')

        with self.assertRaises(SitemapError) as cm:
            self.parse(inp)
        self.assertEqual(cm.exception.lineno, 1)
        self.assertEqual(cm.exception.column, 0)


class TestStandaloneParser(unittest.TestCase):

    def setUp(self):
        self.doc_database = DocDatabase()
        self.link_resolver = LinkResolver(self.doc_database)

    def test_symbol_lists(self):
        inp = (u'### A title\n'
               '\n'
               'A paragraph with *an inline*\n'
               '\n'
               '* [A link with no url]()\n'
               '* [A_link_with_a_url](test.com)\n'
               '* [A link followed by stuff](test.com) stuff\n')

        ast = cmark.hotdoc_to_ast(inp, None)

        # The empty link should have been filtered out
        self.assertEqual(
            cmark.ast_to_html(ast, self.link_resolver),
            (u'<h3>A title</h3>\n'
             '<p>A paragraph with <em>an inline</em></p>\n'
             '<ul>\n'
             '<li><a href="test.com">A_link_with_a_url</a></li>\n'
             '<li><a href="test.com">A link followed by stuff</a> stuff</li>\n'
             '</ul>\n'))

        # And collected in the symbol names
        self.assertListEqual(
            cmark.symbol_names_in_ast(ast),
            [u'A link with no url'])
