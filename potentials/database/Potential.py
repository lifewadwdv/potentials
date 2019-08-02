# Standard libraries
import uuid
import datetime
from pathlib import Path

from DataModelDict import DataModelDict as DM

import requests

from .Citation import Citation
from ..tools import aslist
from .. import rootdir

class Potential(object):
    """
    Class for representing full Potential metadata records.
    """
    def __init__(self, model=None, dois=None, elements=None, key=None,
                 othername=None, fictional=False, modelname=None,
                 notes=None, date=None):
        """
        Creates a new Potential object.

        Parameters
        ----------
        model
        dois
        elements
        key
        othername
        fictional
        modelname
        date
        notes
        """

        if model is not None:
            # Load existing record
            try:
                assert dois is None
                assert elements is None
                assert key is None
                assert othername is None
                assert fictional is False
                assert modelname is None
                assert date is None
                assert notes is None
            except:
                raise TypeError('model cannot be given with any other parameter')
            else:
                self.load(model)
            
        else:
            # Build new record
            self.elements = elements
            self.dois = dois
            self.key = key
            self.date = date
            self.othername = othername
            self.fictional = fictional
            self.modelname = modelname
            self.notes = notes
    
    @property
    def key(self):
        return self.__key
    
    @key.setter
    def key(self, v):
        if v is None:
            self.__key = str(uuid.uuid4())
        else:
            self.__key = str(v)

    @property
    def date(self):
        return self.__date
    
    @date.setter
    def date(self, v):
        if v is None:
            self.__date = datetime.date.today()
        elif isinstance(v, datetime.date):
            self.__date = v
        elif isinstance(v, str):
            self.__date = datetime.date.fromisoformat(v)
        else:
            raise TypeError('Invalid date type')

    @property
    def dois(self):
        return self.__dois

    @dois.setter
    def dois(self, value):
        if value is None:
            self.__dois = None
        else:
            self.__dois = aslist(value)
        self.load_citations()

    @property
    def elements(self):
        return self.__elements

    @elements.setter
    def elements(self, value):
        if value is None:
            self.__elements = None
        else:
            self.__elements = aslist(value)
    
    @property
    def othername(self):
        return self.__othername
    
    @othername.setter
    def othername(self, value):
        if value is None:
            self.__othername = None
        else:
            self.__othername = str(value)
    
    @property
    def fictional(self):
        return self.__fictional
    
    @fictional.setter
    def fictional(self, value):
        assert isinstance(value, bool)
        self.__fictional = value
    
    @property
    def modelname(self):
        return self.__modelname
    
    @modelname.setter
    def modelname(self, value):
        if value is None:
            self.__modelname = None
        else:
            self.__modelname = str(value)

    @property
    def notes(self):
        return self.__notes

    @notes.setter
    def notes(self, value):
        if value is None:
            self.__notes = None
        else:
            self.__notes = str(value)

    def load_citations(self):
        if self.dois is not None:
            self.citations = []
            for doi in self.dois:
                self.citations.append(Citation(doi))
        else:
            self.citations = None

    @classmethod
    def fetch(cls, key, localdir=None, verbose=True):
        """
        Fetches saved potential content.  First checks localdir, then
        potentials github.

        Parameters
        ----------
        key : str
            The potential key to load.
        localdir : Path, optional
            The local directory for the potential JSON files.  If not given,
            will use the default path in potentials/data/potential directory.
        """
        if localdir is None:
            localdir = Path(rootdir, '..', 'data', 'potential')
        localfile = Path(localdir, f'{key}.json')
        
        if localfile.is_file():
            if verbose:
                print('potential loaded from localdir')
            return cls(model=localfile)
            
        else:
            r = requests.get(f'https://github.com/lmhale99/potentials/raw/master/data/potential/{key}.json')
            try:
                r.raise_for_status()
            except:
                raise ValueError(f'no potential with key {key} found')
            else:
                if verbose:
                    print('potential downloaded from github')
                return cls(model=r.text)

    def save(self, localdir=None):
        """
        Saves content locally

        Parameters
        ----------
        localdir : Path, optional
            The local directory for the potential JSON files.  If not given,
            will use the default path in potentials/data/potential directory.
        """
        if localdir is None:
            localdir = Path(rootdir, '..', 'data', 'potential')

        localfile = Path(localdir, f'{self.key}.json')

        with open(localfile, 'w', encoding='UTF-8') as f:
            self.build().json(fp=f, indent=4)

    def build(self):
        """
        Builds Potential model content.
        """
        # Initialize model
        model = DM()
        model['interatomic-potential'] = potential = DM()
        
        # Build identifiers
        potential['key'] = self.key
        potential['id'] = self.id
        potential['record-version'] = str(self.date)

        # Build description
        potential['description'] = description = DM()
        if self.dois is not None:
            for doi in self.dois:
                description['citation'] = DM([('DOI', doi)])
        if self.notes is not None:
            description['notes'] = DM([('text', self.notes)])
        
        # Build element information
        if self.fictional:
            for element in self.elements:
                potential.append('fictional-element', element)
        else:
            for element in self.elements:
                potential.append('element', element)
        if self.othername is not None:
            potential['other-element'] = self.othername

        return model

    def load(self, model):
        """
        Load a Potential model into the Potential class.

        Parameters
        ----------
        model : str or DataModelDict
            Model content or file path to model content.
        """
        # Load model
        self.model = DM(model)
        potential = self.model['interatomic-potential']
        
        # Extract information
        self.key = potential['key']
        self.date = potential['record-version']
        
        description = potential['description']
        dois = []
        for citation in description.iteraslist('citation'):
            dois.append(citation['DOI'])
        self.dois = dois
        if 'notes' in description:
            self.notes = description['notes']['text']
        else:
            self.notes = None
        
        #self.load_citations()

        felements = potential.aslist('fictional-element')
        oelements = potential.aslist('other-element')
        elements = potential.aslist('element')
        
        if len(felements) > 0:
            assert len(elements) == 0
            self.fictional = True
            self.elements = felements
        else:
            assert len(elements) > 0
            self.fictional = False
            self.elements = elements
        if len(oelements) > 0:
            assert len(oelements) == 1
            self.othername = oelements[0]
        else:
            self.othername = None
        
        self.modelname = None
        if self.id != potential['id']:
            self.modelname = str(potential['id']).split('-')[-1]
            if self.id != potential['id']:
                raise ValueError(f"Different ids: {self.id} != {potential['id']}")

    @property
    def id(self):
        try:
            first_citation = self.citations[0]
        except:
            return None
        authors = first_citation.author_dicts()
        year = first_citation.content['year']
        
        potential_id = str(year) + '-'
        
        if len(authors) <= 4:
            for author in authors:
                potential_id += '-' + author['surname']
                potential_id += '-' + author['givenname'].replace('-', '').replace('.', '-').strip('-')
        else:
            for author in authors[:3]:
                potential_id += '-' + author['surname']
                potential_id += '-' + author['givenname'].replace('-', '').replace('.', '-').strip('-')
            potential_id += '-et-al'
        potential_id += '-'
        
        if self.fictional:
            potential_id += '-fictional'
        
        if self.othername is not None:
            potential_id += '-' + str(self.othername)
        else:
            for element in self.elements:
                potential_id += '-' + element
        
        if self.modelname is not None:
            potential_id += '-' + str(self.modelname)
        
        replace_keys = {"'":'', 'á':'a', 'ä':'a', 'ö':'o', 'ø':'o', ' ':'-', 'č':'c', 'ğ':'g', 'ü':'u', 'é':'e', 'Ç':'C', 'ı': 'i'}
        for k,v in replace_keys.items():
            potential_id = potential_id.replace(k,v)
        
        return potential_id