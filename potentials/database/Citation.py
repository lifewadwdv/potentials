from pathlib import Path
import string

import requests

# https://github.com/sckott/habanero
from habanero import cn

# https://bibtexparser.readthedocs.io/en/master/
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode
from bibtexparser.bibdatabase import BibDatabase

from .. import rootdir

class Citation():

    def __init__(self, doi, localdir=None, verbose=True):
        if Path(doi).is_file():
            self.load(doi)
        else:
            self.fetch(doi, localdir=localdir, verbose=verbose)

    def __str__(self):
        return f'Citation doi:{self.doi}'

    @property
    def doi(self):
        """str : The citation's doi"""
        return self.__doi

    @property
    def content(self):
        """dict : The bibtex content fields"""
        return self.__content

    def load(self, path):
        with open(path, encoding='UTF-8') as f:
            entry = f.read()

        # Parse and extract content
        parser = BibTexParser()
        parser.customization = convert_to_unicode
        bibdatabase = bibtexparser.loads(entry, parser=parser)
        
        # Set object attributes
        self.__bibdatabase = bibdatabase
        self.__content = self.__bibdatabase.entries[0]
        self.__doi = self.content['doi']

    def localfilepath(self, doi=None, localdir=None):
        """
        Defines the local file path for the associated .bib file.  The file
        name is generated by transforming the doi into file name compatible
        symbols.
        
        Parameters
        ----------
        doi : str, optional
            The doi to use.  If not given, will use the object's current doi.
        localdir : Path, optional
            The local directory for the .bib files.  If not given, will use
            the default path in potentials/data/bibtex directory.

        Returns
        -------
        pathlib.Path
            The path for the local .bib file
        """
        if doi is None:
            doi = self.doi
        if localdir is None:
            localdir = Path(rootdir, '..', 'data', 'bibtex')

        return Path(localdir, doi.replace('/', '_') + '.bib')

    def fetch(self, doi, localdir=None, verbose=True):
        """
        Fetches bibtex for published content.  First checks localdir, then
        potentials github, then CrossRef.

        Parameters
        ----------
        doi : str or list
            The reference doi to fetch content for.
        localdir : Path, optional
            The local directory for the .bib files.  If not given, will use
            the default path in potentials/data/bibtex directory.
        """
        localfile = self.localfilepath(doi=doi, localdir=localdir)
        if localfile.is_file():
            # Load bibtex from file
            with open(localfile, encoding='UTF-8') as f:
                entry = f.read()
            if verbose:
                print(f'bibtex loaded {doi} from localdir')
        else:
            try:
                r = requests.get(f'https://github.com/lmhale99/potentials/raw/master/data/bibtex/{localfile.name}')
                r.raise_for_status()
                entry = r.text
                if verbose:
                    print(f'bibtex downloaded {doi} from github')
            except:
                # Download using habanero
                entry = cn.content_negotiation(ids=doi, format="bibtex")
                if verbose:
                    print(f'bibtex downloaded {doi} from CrossRef')

        # Parse and extract content
        parser = BibTexParser()
        parser.customization = convert_to_unicode
        bibdatabase = bibtexparser.loads(entry, parser=parser)
        
        # Set object attributes
        self.__doi = doi
        self.__bibdatabase = bibdatabase
        self.__content = self.__bibdatabase.entries[0]

    def save(self, localdir=None):
        """
        Saves content locally

        Parameters
        ----------
        localdir : Path, optional
            The local directory for the .bib files.  If not given, will use
            the default path in potentials/data/bibtex directory.
        """
        localfile = self.localfilepath(localdir=localdir)

        with open(localfile, 'w', encoding='UTF-8') as f:
            bibtexparser.dump(self.__bibdatabase, f)

    @property
    def html(self):
        """str : Formatted html of citation"""
        
        htmlstr = ''

        if 'author' in self.content:
            author_dicts = self.author_dicts()
            numauthors = len(author_dicts)
            for i, author_dict in enumerate(author_dicts):

                # Add formatted names
                givenname = author_dict['givenname']
                surname = author_dict['surname']
                htmlstr += f'{givenname} {surname}'
                
                # Add 'and' and/or comma
                if numauthors >= 3 and i < numauthors - 2:
                    htmlstr += ','
                if numauthors >= 2 and i == numauthors - 2:
                    htmlstr += ' and'
                htmlstr += ' '
        
        if 'year' in self.content:
            htmlstr += f'({self.content["year"]}), '

        if 'title' in self.content:
            htmlstr += f'"{self.content["title"]}", '

        if 'journal' in self.content:
            htmlstr += f'<i>{self.content["journal"]}</i>, '

        if 'volume' in self.content:
            if 'number' in self.content:
                number = f'({self.content["number"]})'
            else:
                number = ''
            
            htmlstr += f'<b>{self.content["volume"]}{number}</b>, '

        if 'pages' in self.content:
            htmlstr += f'{self.content["pages"]} '
        htmlstr = htmlstr.strip() +'. '

        htmlstr += f'DOI: <a href="https://doi.org/{self.doi}">{self.doi}</a>'

        if 'abstract' in self.content:
            htmlstr += f'<br/><b>Abstract:</b> {self.content["abstract"]}'

        return htmlstr

    def author_dicts(self, initials=True):
        """
        Parse bibtex authors field.
        """
        author_dicts = []
        authors = self.content['author']

        # Split authors using 'and'
        authorlist = authors.split(' and ') 
        
        for author in authorlist:
            author_dict = {}
            
            # split given, surname using comma
            if ',' in author:
                index = author.rindex(',')
                author_dict['givenname'] = author[index + 1:].strip()
                author_dict['surname'] = author[:index].strip()

            # split given, surname using rightmost initial
            if '.' in author:  
                index = author.rindex(".")
                author_dict['givenname'] = author[:index + 1].strip()
                author_dict['surname'] = author[index + 1:].strip()
            
            # split given, surname using rightmost space
            else: 
                index = author.rindex(" ")
                author_dict['givenname'] = author[:index + 1].strip()
                author_dict['surname'] = author[index + 1:].strip()
            
            # Change given-name just into initials
            if initials:
                givenname = ''
                for letter in author_dict['givenname'].replace(' ', '').replace('.', ''):
                    if letter in string.ascii_uppercase:
                        givenname += letter +'.'
                    elif letter in ['-']:
                        givenname += letter
                author_dict['givenname'] = givenname
            
            author_dicts.append(author_dict)
        
        return author_dicts