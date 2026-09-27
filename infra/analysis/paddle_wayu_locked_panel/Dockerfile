FROM rocker/r-ver:4.5.2@sha256:fd4ccdd3a4a6f7ef805e2daeee2a0fe3bf126bc231f36351223baecf5a595a4c

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential cmake gfortran libcurl4-openssl-dev libssl-dev \
        libuv1-dev libxml2-dev \
    && command -v cmake \
    && test -f /usr/include/uv.h \
    && rm -rf /var/lib/apt/lists/*

RUN Rscript -e "install.packages('remotes', repos='https://cloud.r-project.org')" \
    && Rscript -e "remotes::install_version('lme4', version='1.1-38', repos='https://cloud.r-project.org', upgrade='never')" \
    && Rscript -e "remotes::install_version('detectseparation', version='0.3', repos='https://cloud.r-project.org', upgrade='never')" \
    && Rscript -e "remotes::install_version('jsonlite', version='2.0.0', repos='https://cloud.r-project.org', upgrade='never')"

RUN install -d /opt/locked-panel
COPY run_glmm.R /opt/locked-panel/run_glmm.R
COPY validate_environment.R /opt/locked-panel/validate_environment.R

# This assertion is intentionally a separate build layer. remotes may report an
# install failure as an R warning while Rscript still exits zero; the validator
# makes any missing/wrong package, unloadable library, missing entrypoint,
# unparseable entrypoint, or entrypoint hash mismatch fail the Docker build.
RUN Rscript /opt/locked-panel/validate_environment.R

WORKDIR /analysis
ENTRYPOINT ["Rscript", "/opt/locked-panel/run_glmm.R"]
