import dagger
from dagger import dag, function, object_type
import requests
from dataclasses import dataclass
import bs4
import re
from bs4 import BeautifulSoup
from collections import defaultdict
from typing import Iterable, List

# @object_type
@dataclass
class GettextVersion:
    tarball_url: str
    sig_url: str
    version: str

    @staticmethod
    def mirror() -> str:
        return "https://mirrors.ocf.berkeley.edu/gnu/"

    @staticmethod
    def base_url() -> str:
        return GettextVersion.mirror() + "/gettext/"

    @staticmethod
    def tarball_base_url() -> str:
        return GettextVersion.base_url() + "/gettext-%version%.tar.gz"
    
    @staticmethod
    def from_version(version: str) -> 'GettextVersion':
        return GettextVersion(
            version=version,
            tarball_url=GettextVersion.tarball_base_url().replace('%version%', version),
            sig_url=GettextVersion.base_url() + f"gettext-{version}.tar.gz.sig"
        )

    @staticmethod
    def get_versions() -> Iterable['GettextVersion']:
        regex = r"gettext-(?P<version>.*?).tar.gz(?P<sig>\.sig)?"
        res = requests.get(GettextVersion.base_url())
        tree = BeautifulSoup(res.text)
        versions = defaultdict(lambda: {})
        for item in tree.find("table").children:
            # print(type(item))
            item = item.find('a')
            if type(item) is int:
                continue
            if item is None:
                continue
            name = item.text
            href = item.get('href')
            match = re.match(regex, name)
            if match is None:
                continue
            match = match.groupdict()
            has_sig = match['sig'] is not None
            versions[match['version']]['sig_url' if has_sig else 'tarball_url'] = href
        print(versions)
        for (k, v) in versions.items():
            yield GettextVersion(
                tarball_url=GettextVersion.base_url() + v['tarball_url'],
                sig_url=GettextVersion.base_url() + v['sig_url'],
                version=k
            )

@object_type
class MiseGettextDagger:
    @function
    async def teste_build(self, version: str = "0.26") -> dagger.Directory:
        source = await self.fetch_source(GettextVersion.from_version(version))
        return source

    @function
    async def fetch_tarball(self, tarball: dagger.File, signature: dagger.File, valid_keys: List[str] =[]) -> dagger.Directory:
        return (
            await dag.container()
            .from_("alpine:latest")
            .with_exec(["apk", "add", "gnupg"])
            .with_file("/source.tar", tarball)
            .with_file("/signature.sig", signature)
            .with_exec(["gpg", "--recv-keys", *valid_keys])
            .with_exec(["gpg", "--verify", "signature.sig", "source.tar"])
            .with_exec(["mkdir", "-p", "/src"])
            .with_exec(["tar", "-xvf", "/source.tar", "-C", "/src", "--strip-components", "1"])
            .directory("/src")
        )

    def fetch_source(self, version: GettextVersion) -> dagger.Directory:
        return self.fetch_tarball(
            tarball=dag.http(version.tarball_url),
            signature=dag.http(version.sig_url),
            valid_keys=["B6301D9E1BBEAC08", "F5BE8B267C6A406D", "4F494A942E4616C2"]
        )
            
    
    @function
    def base_container(self) -> dagger.Container:
        return dag.container().from_("debian:stable")

    @function
    def build_linux(self, source: dagger.Directory) -> dagger.Directory:
        return source # TODO: fazer

if __name__ == '__main__':
    print(list(GettextVersion.get_versions()))
