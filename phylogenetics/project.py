import os
import pickle
import subprocess
import pandas as pd
import phylopandas as ph

import Bio.Phylo.Applications

import pyasr

class PhylogeneticsProject(object):
    """A lightweight Python object that populates a PhyloPandas DataFrame.

    Parameters
    ----------
    project_dir : str
        the directory to store the phylogenetic data.

    overwrite : bool (default: False)
        allow overwriting a project that already exists in project_dir location.
    """
    def __init__(self, project_dir, overwrite=False):

        # Set up a project directory
        if os.path.exists(project_dir) and overwrite is False:
            raise Exception("Project already exists! Use `PhylogeneticsProject.load_pickle` or delete the project.")
        elif not os.path.exists(project_dir):
            os.makedirs(project_dir)

        # Define columns for project.
        columns = [
            'uid',
            'description',
            'id',
            'label',
            'sequence',
            'type',
            'parent',
            'branch_length'
        ]

        self.project_dir = project_dir
        self.data = pd.DataFrame(columns=columns)

    @staticmethod
    def load_pickle(filename):
        """Loads data from another project that was saved using `to_pickle`.

        Parameters
        ----------
        filename : str
            the full path to the pickle file to be loaded.
        """
        with open(filename, 'rb') as f:
            self = pickle.load(f)
            return self

    def to_pickle(self, filename):
        """Saves the PhylogeneticsProject as a pickle file that can be loaded
        into a different project or at a later date.

        Parameters
        ----------
        filename : str
            the full path to the pickle file to be saved
        """
        with open(filename, 'wb') as f:
            pickle.dump(self, f)

    def read_data(self, path, schema, **kwargs):
        """
        """
        method_name = 'read_{}'.format(schema)
        try:
            method = getattr(self.data.phylo, method_name)
        except:
            method = getattr(self.data, method_name)
        self.data = method(path, **kwargs)

    def compute_tree(
        self,
        sequence_col='sequence',
        datatype='aa',
        bootstrap='-1',
        model='LG',
        frequencies='e',
        **kwargs):
        """Compute tree."""
        fname = "compute_tree.phy"
        path = os.path.join(self.project_dir, fname)

        # Write out path
        self.data.phylo.to_phylip(filename=path)

        # Prepare options for PhyML.
        options = {
            'input':path,
            'datatype':datatype,
            'bootstrap':bootstrap,
            'model':model,
            'frequencies':frequencies,
        }

        # Update with any kwargs manually set by users.
        options.update(**kwargs)

        # ----- Flexibility here to use different ext apps -----

        # Build command line arguments for PhyML.
        cml = Bio.Phylo.Applications.PhymlCommandline(**options)
        cml_args = str(cml).split()
        output = subprocess.run(cml_args)

        # Get path (catch variations in file extension generated by phyml)
        outfile = "compute_tree.phy_phyml_tree"
        outpath = os.path.join(self.project_dir, outfile)

        # Old versions of phyml have .txt at end.
        if not os.path.exists(outpath):
            outpath += '.txt'

        # ------------------------------------------------------

        # Update dataframe
        tree_data = ph.read_newick(outpath)

        # Swap ids and uids for leaf nodes
        tree_data.loc[tree_data.type == 'leaf', 'uid'] = tree_data.id

        # Add to main dataframe
        self.data = self.data.phylo.combine(tree_data, on='uid')


    def compute_reconstruction(
        self,
        id_col='uid',
        sequence_col='sequence',
        altall_cutoff=0.2,
        aaRatefile='lg',
        **kwargs
        ):
        """Run ancestral sequence reconstruction powered by PAML,

        Parameters
        ----------

        """
        df = pyasr.reconstruct(
            self.data,
            id_col=id_col,
            sequence_col=sequence_col,
            working_dir=self.project_dir,
            altall_cutoff=altall_cutoff,
            aaRatefile=aaRatefile,
            **kwargs
        )
        self.data = df
