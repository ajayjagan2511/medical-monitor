# Scrapers package
from scrapers.kaggle_scraper import KaggleScraper
from scrapers.huggingface_scraper import HuggingFaceScraper
from scrapers.zenodo_scraper import ZenodoScraper
from scrapers.pubmed_scraper import PubMedScraper
from scrapers.tcia_scraper import TCIAScraper
from scrapers.synapse_scraper import SynapseScraper
from scrapers.grandchallenge_scraper import GrandChallengeScraper
from scrapers.harvard_scraper import HarvardScraper
from scrapers.openi_scraper import OpenIScraper
from scrapers.isic_scraper import ISICScraper
from scrapers.midrc_scraper import MIDRCScraper
from scrapers.stanford_scraper import StanfordScraper

__all__ = [
    "KaggleScraper",
    "HuggingFaceScraper",
    "ZenodoScraper",
    "PubMedScraper",
    "TCIAScraper",
    "SynapseScraper",
    "GrandChallengeScraper",
    "HarvardScraper",
    "OpenIScraper",
    "ISICScraper",
    "MIDRCScraper",
    "StanfordScraper",
]
