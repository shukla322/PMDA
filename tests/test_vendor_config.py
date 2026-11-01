import importlib
from pathlib import Path
import sys
import tomllib
import unittest


class WindowsBuilderTests(unittest.TestCase):
    def test_learning_paths_roundtrip_as_literal_windows_paths(self):
        vendor=Path(__file__).resolve().parents[1] / "vendor/solitarius-mcp"
        sys.path.insert(0,str(vendor))
        try:
            tl=importlib.import_module("config_builders.tl_config")
            rl=importlib.import_module("config_builders.rl_config")
            model=r'C:\Users\researcher\BTP\model.prior'
            smiles=r'C:\Users\researcher\BTP\data.smi'
            output=r'C:\Users\researcher\BTP\out.model'
            parsed=tomllib.loads(tl.build_tl_toml(model,smiles,output,num_epochs=1,batch_size=16,tb_logdir=r'C:\Users\researcher\BTP\logs'))
            self.assertEqual(parsed["parameters"]["input_model_file"],model)
            self.assertEqual(parsed["parameters"]["smiles_file"],smiles)
            parsed=tomllib.loads(rl.build_rl_toml(model,model,output,stages=[{"chkpt_file":output,"max_steps":2,"min_steps":2,"scoring":{"components":[{"component_type":"QED"}]}}]))
            self.assertEqual(parsed["parameters"]["prior_file"],model)
            self.assertEqual(parsed["stage"][0]["chkpt_file"],output)
            self.assertNotIn("unique_sequences",parsed["parameters"])
        finally:
            sys.path.remove(str(vendor))
