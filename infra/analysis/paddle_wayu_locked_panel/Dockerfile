FROM rocker/r-ver:4.5.2

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential gfortran libcurl4-openssl-dev libssl-dev libxml2-dev \
    && rm -rf /var/lib/apt/lists/*

RUN Rscript -e "install.packages('remotes', repos='https://cloud.r-project.org')" \
    && Rscript -e "remotes::install_version('lme4', version='1.1-38', repos='https://cloud.r-project.org', upgrade='never')" \
    && Rscript -e "remotes::install_version('detectseparation', version='0.3', repos='https://cloud.r-project.org', upgrade='never')" \
    && Rscript -e "remotes::install_version('jsonlite', version='2.0.0', repos='https://cloud.r-project.org', upgrade='never')"

WORKDIR /analysis
ENTRYPOINT ["Rscript", "/opt/locked-panel/run_glmm.R"]
