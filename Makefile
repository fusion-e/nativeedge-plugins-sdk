# Makefile for collecting and installing requirements for nativeedge-plugins-sdk.
VENVS := $(shell pyenv virtualenvs --skip-aliases --bare | grep 'project\b')
FUSION_COMMON := fusion-common
FUSION_AGENT := fusion-agent
FUSION_MANAGER := fusion-manager
BRANCH := master
SHELL := /bin/bash
ifneq ($(GH_USER),)
	DOMAIN=${GH_USER}:${GITHUB_PASSWORD}@eos2git.cec.lab.emc.com/ISG-Edge
else
	DOMAIN=${GH_TOKEN}@github.com/fusion-e
endif

default:
	make download_from_git
	make setup_local_virtual_env
	make run_tests

compile:
	make download_from_git
	make setup_local_virtual_env

download_from_git:
	make download_fusion_common
	make download_fusion_agent
	make download_fusion_manager

setup_local_virtual_env:
ifneq ($(VENVS),)
	@echo We have $(VENVS)
	pyenv virtualenv-delete -f project && pyenv deactivate
endif
	pyenv virtualenv 3.11 project

download_fusion_common:
ifneq ($(wildcard ./${FUSION_COMMON}*),)
	@echo "Found ${FUSION_COMMON}."
else
	git clone https://${DOMAIN}/${FUSION_COMMON}.git ${HOME}/${FUSION_COMMON} && cd ${HOME}/${FUSION_COMMON} && git checkout ${BRANCH} && cd
endif

download_fusion_agent:
ifneq ($(wildcard ./${FUSION_AGENT}*),)
	@echo "Found ${FUSION_AGENT}."
else
	git clone https://${DOMAIN}/${FUSION_AGENT}.git ${HOME}/${FUSION_AGENT} && cd ${HOME}/${FUSION_AGENT} && git checkout ${BRANCH} && cd
endif

download_fusion_manager:
ifneq ($(wildcard ${FUSION_MANAGER}*),)
	@echo "Found ./${FUSION_MANAGER}."
else
	git clone https://${DOMAIN}/${FUSION_MANAGER}.git ${HOME}/${FUSION_MANAGER} && cd ${HOME}/${FUSION_MANAGER}/mgmtworker && git checkout ${BRANCH} && cd
endif

cleanup:
	pyenv virtualenv-delete -f project
	rm -rf ${FUSION_MANAGER} ${FUSION_AGENT} ${FUSION_COMMON}

run_tests:
	@echo "Starting executing the tests."
	HOME=${HOME} VIRTUAL_ENV=${HOME}/.pyenv/${VENVS} tox

clrf:
	@find . \( -path ./.tox -prune -o -path ./.git -prune \) -o -type f -exec dos2unix {} \;

wheels:
	@echo "Creating wheels..."
	@pip wheel ${HOME}/${FUSION_COMMON}/ -w /workspace/build/ --find-links /workspace/build
	@pip wheel ${HOME}/${FUSION_AGENT}/ -w /workspace/build/ --find-links /workspace/build
	@pip wheel ${HOME}/${FUSION_MANAGER}/mgmtworker -w /workspace/build/ --find-links /workspace/build
