# Studious-Tribble

## Strategy

The idea is to employ worker threads that poll the servers for responses and queue it in a shared queue for the aggragators
threads to consume the responses and compute the report. The App uses two Queues, one is used to queue a list of servers to poll 
and the other is used to queue responses from servers. The aggregate workers combine to repsonses into a report summarizing
the success rate per Application and Version

Parameters like the number of Endpoint web scrappers, aggrgator works and path to the servers are configured in a `config.yaml`.
The App reads the `config.yaml` , instantiates the scrappers and aggregators and starts the threads to summarize the responses
in a `Report` object.

The output is collected into a `.csv` file with columns `App Name`, `Version`, `Count` and `Total Count for App` to be 
reused for any applications downstream.

## Requirements
Python 3

## Run Instructions 

1. Update the `num_scrapers` in `config.yaml` with the number of required scrappers 
2. Update the `num_aggregators` in `config.yaml` with the number of required aggregator threads
3. Update the `servers` in `config.yaml` with the absolute path to the file that contains the list of servers
4. Run `python app.py` from the root of the repo

The Success rates are printed to STDOUT while also saved in a file `report.csv` in the same repo.
