#!/usr/bin/env python3

import argparse
import os
import sys
import time
import traceback
import yaml

from catkin_pkg.package import parse_package_string
from rosdistro import get_cached_distribution
from rosdistro import get_index

from ros_buildfarm.argument import add_argument_build_name
from ros_buildfarm.argument import add_argument_output_dir
from ros_buildfarm.argument import add_argument_config_url
from ros_buildfarm.argument import add_argument_rosdistro_name
from ros_buildfarm.config import get_index as get_config_index


def main(argv=sys.argv[1:]):
    parser = argparse.ArgumentParser(
        description="Generate `manifest.yaml` from released package manifests")
    add_argument_config_url(parser)
    add_argument_rosdistro_name(parser)
    add_argument_build_name(parser, 'doc')
    add_argument_output_dir(parser, required=True)
    args = parser.parse_args(argv)

    config = get_config_index(args.config_url)

    index = get_index(config.rosdistro_index_url)
    distribution = get_cached_distribution(index, args.rosdistro_name)

    # get rosdistro distribution cache
    # iterate over all released repositories
    # which don't have a doc entry
    # extract information from package.xml and generate manifest.yaml

    repo_names = get_repo_names_with_release_but_no_doc(distribution)
    pkg_names = get_package_names(distribution, repo_names)

    # TODO black/white

    print("Generate 'manifest.yaml' files for the following packages:")
    api_path = os.path.join(args.output_dir, 'api')
    for pkg_name in sorted(pkg_names):
        print('- %s' % pkg_name)
        try:
            data = get_metadata(distribution, pkg_name)
        except Exception:
            print('Could not extract meta data:', file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            continue
        manifest_yaml = os.path.join(api_path, pkg_name, 'manifest.yaml')
        write_manifest_yaml(manifest_yaml, data)

    return 0


def get_repo_names_with_release_but_no_doc(distribution):
    repo_names = []
    for repo in distribution.repositories.values():
        if not repo.doc_repository and repo.release_repository and \
                repo.release_repository.version:
            repo_names.append(repo.name)
    return repo_names


def get_package_names(distribution, repo_names):
    pkg_names = []
    for repo_name in repo_names:
        repo = distribution.repositories[repo_name]
        pkg_names.extend(repo.release_repository.package_names)
    return pkg_names


def get_metadata(distribution, pkg_name):
    rel_pkg = distribution.release_packages[pkg_name]
    repo_name = rel_pkg.repository_name
    repository = distribution.repositories[repo_name]

    xml = distribution.get_release_package_xml(pkg_name)
    pkg = parse_package_string(xml)

    data = {}
    data['repo_name'] = repo_name
    data['timestamp'] = time.time()

    pkg_status = None
    pkg_status_description = None
    # package level status information
    if pkg.name in repository.status_per_package:
        pkg_status_data = repository.status_per_package[pkg.name]
        pkg_status = pkg_status_data.get('status', None)
        pkg_status_description = pkg_status_data.get(
            'status_description', None)
    # repository level status information
    if pkg_status is None:
        pkg_status = repository.status
    if pkg_status_description is None:
        pkg_status_description = repository.status_description
    if pkg_status is not None:
        data['maintainer_status'] = pkg_status
    if pkg_status_description is not None:
        data['maintainer_status_description'] = pkg_status_description

    data['description'] = pkg.description
    data['maintainers'] = ', '.join([str(m) for m in pkg.maintainers])
    data['license'] = ', '.join(pkg.licenses)

    website_urls = [u.url for u in pkg.urls if u.type == 'website']
    if website_urls:
        data['url'] = website_urls[0]

    data['authors'] = ', '.join([str(a) for a in pkg.authors])

    depends = pkg.build_depends + pkg.buildtool_depends + pkg.run_depends
    data['depends'] = sorted(set([dep.name for dep in depends]))

    is_metapackage = 'metapackage' in pkg.exports
    data['package_type'] = 'metapackage' if is_metapackage else 'package'
    if is_metapackage:
        data['packages'] = sorted([dep.name for dep in pkg.run_depends])

    # TODO list jobs

    return data


def write_manifest_yaml(manifest_yaml, data):
    base_path = os.path.dirname(manifest_yaml)
    if not os.path.exists(base_path):
        os.makedirs(base_path)
    with open(manifest_yaml, 'w+') as f:
        yaml.safe_dump(data, f, default_flow_style=False)
    with open(os.path.join(base_path, 'stamp'), 'w'):
        pass


if __name__ == '__main__':
    sys.exit(main())
