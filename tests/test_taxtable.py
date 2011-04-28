#!/usr/bin/env python

import sys
import os
from os import path
import unittest
import logging

from sqlalchemy import create_engine

import config
from config import funcname, mkdir, rmdir

import taxtastic
from taxtastic.taxonomy import Taxonomy
import taxtastic.ncbi

log = logging

module = path.split(path.splitext(__file__)[0])[1]
outputdir = mkdir(path.join(config.outputdir, module))
datadir = config.datadir

echo = False

zfile = config.ncbi_data
dbname = config.ncbi_master_db


class TestBase(unittest.TestCase):
    
    def setUp(self):
        self.engine = create_engine('sqlite:///%s' % dbname, echo=echo)
        self.tax = Taxonomy(self.engine, taxtastic.ncbi.ranks)

    def tearDown(self):
        self.engine.dispose()
    
class TestTaxonomyInit(TestBase):

    def test01(self):
        self.tax._node('2')

    def test02(self):
        self.assertRaises(KeyError, self.tax._node, 'buh')

class TestGetLineagePrivate(TestBase):

    def test01(self):
        lineage = self.tax._get_lineage('1')
        self.assertTrue(lineage == [('root','1')])

    def test02(self):
        tax_id = '1280' # staph aureus

        self.assertFalse(tax_id in self.tax.cached)
        lineage = self.tax._get_lineage(tax_id)
        self.assertTrue(tax_id in self.tax.cached)
        self.assertTrue(lineage[0][0] == 'root')
        self.assertTrue(lineage[-1][0] == 'species')

    def test03(self):
        tax_id = '30630' # deprecated; Microtus levis Taxonomy ID: 537919

        self.assertFalse(tax_id in self.tax.cached)
        self.assertRaises(KeyError, self.tax._get_lineage, tax_id)

class TestGetMerged(TestBase):

    def test01(self):
        tax_id = '1378'
        merged = self.tax._get_merged(tax_id)
        self.assertTrue(merged is None)

    def test02(self):
        tax_id = '30630' # deprecated; Microtus levis Taxonomy ID: 537919
        merged = self.tax._get_merged(tax_id)
        self.assertFalse(merged is None)

class TestTaxNameSearch(TestBase):

    def test01(self):
        tax_id, tax_name, is_primary = self.tax.primary_from_name('Gemella')
        self.assertTrue(tax_id == '1378')
        self.assertTrue(is_primary)

    def test02(self):
        self.assertRaises(KeyError, self.tax.primary_from_name, 'buggabugga')

    def test03(self):
        tax_id, tax_name, is_primary = self.tax.primary_from_name('Gemella Berger 1960')

        self.assertTrue(tax_id == '1378')
        self.assertFalse(is_primary)


class TestSynonyms(TestBase):

    def test01(self):
        synonyms = self.tax.synonyms(tax_id='1378')

    def test02(self):
        synonyms = self.tax.synonyms(tax_name='Gemella')



class TestGetLineagePublic(TestBase):

    def test01(self):
        lineage = self.tax.lineage('1')

        self.assertTrue(lineage['root'] == '1')
        self.assertTrue(lineage['rank'] == 'root')

    def test02(self):
        tax_id = '1280' # staph aureus

        self.assertFalse(tax_id in self.tax.cached)
        lineage = self.tax.lineage(tax_id)
        self.assertTrue(tax_id in self.tax.cached)
        self.assertTrue(lineage['rank'] == 'species')

        keys = set(lineage.keys())
        ranks = set(self.tax.ranks)
        self.assertTrue(keys - ranks == set(['parent_id', 'tax_id', 'rank', 'tax_name']))

    def test03(self):
        tax_id = '1378' # Gemella; lineage has two successive no_rank taxa
        lineage = self.tax.lineage(tax_id)
        self.assertTrue(lineage['rank'] == 'genus')

        keys = set(lineage.keys())
        ranks = set(self.tax.ranks)
        self.assertTrue(keys - ranks == set(['parent_id', 'tax_id', 'rank', 'tax_name']))

    def test04(self):
        self.assertRaises(ValueError, self.tax.lineage, tax_id=None, tax_name=None)

    def test05(self):
        self.assertRaises(ValueError, self.tax.lineage, tax_id='1', tax_name='root')

    def test06(self):
        tax_id = '1378' # Gemella; lineage has two successive no_rank taxa
        tax_name = 'Gemella'
        lineage = self.tax.lineage(tax_name=tax_name)

        # lineage = self.tax.lineage(tax_id)
        # self.assertTrue(lineage['rank'] == 'genus')

    # def test07(self):
    #     ## TODO: handle deprecated tax_ids

    #     tax_id = '30630' # deprecated; Microtus levis Taxonomy ID: 537919
    #     lineage = self.tax.lineage(tax_id=tax_id)
        
        
class TestMethods(TestBase):

    def test01(self):
        taxname = self.tax.primary_from_id('1280')
        self.assertTrue(taxname == 'Staphylococcus aureus')

    def test02(self):
        self.assertRaises(KeyError, self.tax.primary_from_id, 'buh')

    def test03(self):
        res = self.tax.add_source(name='new source', description='really new!')
        res = self.tax.add_source(name='new source', description='really new!')
        self.assertTrue(res == (2, False))


    # def test04(self):
    #     self.tax.add_node(tax_id = "186802_1",
    #                       parent_id = "186802",
    #                       rank = "species",
    #                       source_name = "Fredricks Lab",
    #                       tax_name = 'BVAB1')


class TestWriteTable(TestBase):
    """
    test tax.write_table - note that this method produces output.

    TODO: write output to subdirectory named for the test method
    """
    
    def setUp(self):
        super(TestWriteTable, self).setUp()
        self.funcname = funcname(self.id())
        self.fname = os.path.join(outputdir, self.funcname)+'.csv'

    def test02(self):
        tax_id = '1280' # staph aureus
        lineage = self.tax.lineage(tax_id)

        with open(self.fname,'w') as fout:
            self.tax.write_table(taxa=None, csvfile=fout)

    def test03(self):
        tax_id = '1378' # Gemella; lineage has two successive no_rank taxa
        lineage = self.tax.lineage(tax_id)

        with open(self.fname,'w') as fout:
            self.tax.write_table(taxa=None, csvfile=fout)

    def test04(self):
        tax_id = '1378' # Gemella; lineage has two successive no_rank taxa
        for tax_id in ['1378','1280','131110']:
            lineage = self.tax.lineage(tax_id)

        with open(self.fname,'w') as fout:
            self.tax.write_table(taxa=None, csvfile=fout)




        
