#!/usr/bin/env python

# Copyright (c) Microsoft Corporation
# All rights reserved.
#
# MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
# to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED *AS IS*, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
# BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

from __future__ import print_function

import yaml
import os
import sys
import jinja2
import argparse
import logging
import logging.config

from paiLibrary.common import linux_shell
from paiLibrary.common import file_handler
from paiLibrary.clusterObjectModel import objectModelFactory
from paiLibrary.paiBuild import build_center
from paiLibrary.paiBuild import push_center



logger = logging.getLogger(__name__)



def setup_logging():
    """
    Setup logging configuration.
    """
    configuration_path = "sysconf/logging.yaml"
    logging_configuration = file_handler.load_yaml_config(configuration_path)
    logging.config.dictConfig(logging_configuration)



def load_cluster_objectModel_service(config_path):

    objectModel = objectModelFactory.objectModelFactory(config_path)
    ret = objectModel.objectModelPipeLine()

    return ret["service"]



def login_docker_registry(docker_registry, docker_username, docker_password):

    shell_cmd = "docker login -u {0} -p {1} {2}".format(docker_username, docker_password, docker_registry)
    error_msg = "docker registry login error"
    linux_shell.execute_shell(shell_cmd, error_msg)
    logger.info("docker registry login successfully")



def generate_secret_base64code(docker_info):

    domain = str(docker_info[ "docker_registry_domain" ])
    username = str(docker_info[ "docker_username" ])
    passwd = str(docker_info[ "docker_password" ])

    if domain == "public":
        domain = ""

    if username and passwd:
        login_docker_registry( domain, username, passwd )

        base64code = linux_shell.execute_shell_with_output(
            "cat ~/.docker/config.json | base64",
            "Failed to base64 the docker's config.json"
        )
    else:
        logger.info("docker registry authentication not provided")

        base64code = "{}".encode("base64")

    docker_info["base64code"] = base64code.replace("\n", "")



def generate_docker_credential(docker_info):

    username = str(docker_info[ "docker_username" ])
    passwd = str(docker_info[ "docker_password" ])

    if username and passwd:
        credential = linux_shell.execute_shell_with_output(
            "cat ~/.docker/config.json",
            "Failed to get the docker's config.json"
        )
    else:
        credential = "{}"

    docker_info["credential"] = credential



def generate_image_url_prefix(docker_info):

    domain = str(docker_info["docker_registry_domain"])
    namespace = str(docker_info["docker_namespace"])

    if domain != "public":
        prefix = "{0}/{1}/".format(domain, namespace)
    else:
        prefix = "{0}/".format(namespace)

    docker_info["prefix"] = prefix



def generate_configuration_of_hadoop_queues(cluster_config):
    #
    hadoop_queues_config = {}
    #
    total_weight = 0
    for vc_name in cluster_config["clusterinfo"]["virtualClusters"]:
        vc_config = cluster_config["clusterinfo"]["virtualClusters"][vc_name]
        weight = float(vc_config["capacity"])
        hadoop_queues_config[vc_name] = {
            "description": vc_config["description"],
            "weight": weight
        }
        total_weight += weight
    hadoop_queues_config["default"] = {
        "description": "Default virtual cluster.",
        "weight": max(0, 100 - total_weight)
    }
    if total_weight > 100:
        logger.warning("Too many resources configured in virtual clusters.")
        for hq_name in hadoop_queues_config:
            hq_config = hadoop_queues_config[hq_name]
            hq_config["weight"] /= (total_weight / 100)
    #
    cluster_config["clusterinfo"]["hadoopQueues"] = hadoop_queues_config



def cluster_object_model_generate_service(config_path):

    cluster_config = load_cluster_objectModel_service(config_path)

    generate_secret_base64code(cluster_config[ "clusterinfo" ][ "dockerregistryinfo" ])
    generate_docker_credential(cluster_config[ "clusterinfo" ][ "dockerregistryinfo" ])
    generate_image_url_prefix(cluster_config[ "clusterinfo" ][ "dockerregistryinfo" ])

    if 'docker_tag' not in cluster_config['clusterinfo']['dockerregistryinfo']:
        cluster_config['clusterinfo']['dockerregistryinfo']['docker_tag'] = 'latest'

    generate_configuration_of_hadoop_queues(cluster_config)




def pai_build_info():

    logger.error("The command is wrong.")
    logger.error("Build image: paictl.py image build -p /path/to/configuration/ [ -n image-x ]")
    logger.error("Push image : paictl.py image push -p /path/to/configuration/ [ -n image-x ]")




def pai_build():

    if len(sys.argv) < 2:
        pai_build_info()
        return

    option = sys.argv[1]
    del sys.argv[1]

    if option not in ["build", "push"]:
        pai_build_info()
        return

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--config-path', dest = "config_path", required=True, help="The path of your configuration directory.")
    parser.add_argument('-n', '--image-name', dest = "image_name", default='all', help="Build and push the target image to the registry")
    args = parser.parse_args(sys.argv[1:])

    config_path = args.config_path
    image_name = args.image_name
    cluster_object_model = load_cluster_objectModel_service(config_path)

    image_list = None
    if image_name != "all":
        image_list = [ image_name ]

    if option == "build":
        center = build_center.build_center(cluster_object_model, image_list)
        center.run()

    if option == "push":
        center = push_center.push_center(cluster_object_model, image_list)
        center.run()



def pai_control():

    None




def k8s_control():

    None




def easy_way_deploy():

    None



def main():

    if len(sys.argv) < 2:
        logger.error("You should pass at least one argument")
        return

    module = sys.argv[1]
    del sys.argv[1]

    if module == "image":

        pai_build()

    elif module == "k8s-control":

        None

    elif module == "pai-control":

        None

    elif module == "easy-way-deploy":

        None

    elif module == "have-a-try":

        None

    else:

        logger.error("Sorry, there is no definition of the argument [{0}]".format(module))





if __name__ == "__main__":

    setup_logging()
    main()
