"""
Works with a directory of anndata objects which are the result of the stuart lab
runs from October 2018

Update the data values common across the cluster solution, such as
cluster_description, method...

To run change the DATADIR and FULLPATHDB global run and run the script from the repos venv.

python stuart_lab_anndata_in.py
"""
import os
import scanpy as sc
import pandas as pd
from sqlalchemy import create_engine, Table, MetaData, select

# Full path to the sqllite db
#FULLDBPATH = "/home/duncan/work/singlecelldb-ingest"
FULLDBPATH = "/Users/swat/dev/cdb/cluster.db"
# Path to the data directory filled with ebi anndata objects.
DATADIR = "/Users/swat/dev/cdbIngest/dataIn"

# Connection to the database.
dbstartstr = "sqlite:///%s" % FULLDBPATH
engine = create_engine(dbstartstr, echo=False)
#engine = create_engine(dbstartstr, echo=True)
metadata = MetaData()
conn = engine.connect()

# Accessor for each of the tables.
dataset = Table('dataset', metadata, autoload=True, autoload_with=engine)
cluster_solution_table = Table('cluster_solution', metadata, autoload=True, autoload_with=engine)
cluster = Table('cluster', metadata, autoload=True, autoload_with=engine)
cell_of_cluster = Table('cell_of_cluster', metadata, autoload=True, autoload_with=engine)

def cluster_solution_name():
    return "louvain100pcs"


def cluster_description():
    return "default scanpy clustering"


def method():
    return "louvain clustering on the 100 first principal components"


def method_implementation():
    return "scanpy.api.tl.louvain"


def method_url():
    return "https://scanpy.readthedocs.io/en/latest/api/scanpy.api.tl.louvain.html"


def method_parameters():
    return "default parameters in scanpy.api.tl.louvain"


def analyst():
    return "Verena Friedl"


# Read each anndata object.
for filename in os.listdir(DATADIR):
    print(filename)
    ad = sc.read(os.path.join(DATADIR,filename))

    # Note that datasets were loaded via swagger update APIs.

    # Find the dataset_id
    dataset_name = filename.split("_clustered")[0]
    print("**************************************")
    print('dataset_name:', dataset_name)

    rows = select(
        [dataset.c.name, dataset.c.id]).where(dataset.c.name == dataset_name)
    result = conn.execute(rows)
    for row in result:
        dataset_id = row['id']
        name = row['name']
    #print('dataset id, name:', dataset_id, name)

    # Load the cluster solution into the DB.
    cluster_sol_ins = cluster_solution_table.insert().values(
        name=cluster_solution_name(),
        description=cluster_description(),
        method=method(),
        method_implementation=method_implementation(),
        method_url=method_url(),
        method_parameters=method_parameters(),
        analyst=analyst(),
        dataset_id=dataset_id
        )
    result = conn.execute(cluster_sol_ins)
    cluster_sol_key = result.inserted_primary_key
    #print('cluster_sol_key:', cluster_sol_key)

    # Load the cluster into the DB.
    cluster_solution = ad.obs.louvain
    cluster_names = cluster_solution.unique().tolist()
    cluster_names.sort()
    print('cluster_names', cluster_names)
    for cluster_name in cluster_names:
        cluster_ins = cluster.insert().values(
                name=str(cluster_name),
                cluster_solution_id=cluster_sol_key[0]
                )
        result = conn.execute(cluster_ins)
        cluster_key = result.inserted_primary_key
        #print('cluster_key:', cluster_key)

        # Load the cell assignments for this cluster.
        cell_ids = cluster_solution[cluster_solution == cluster_name].index
        cells = [dict(name=n, cluster_id=cluster_key[0]) for n in cell_ids]
        #print(cells)
        conn.execute(cell_of_cluster.insert(), cells)
