import pandas as pd
import numpy as np
import typing
import os

class KB_Dec:
	def __init__(self, path:typing.Union[str, bytes, os.PathLike]=None) -> None:
		if path is not None:
			self.load_kb_dec(path)
		else:
			self.df_map_1_1 = pd.DataFrame()
			self.df_map_2_1 = pd.DataFrame()
			self.df_map_max_or = pd.DataFrame()
			self.df_best_before = pd.DataFrame()
	
	def load_kb_dec(self, path:typing.Union[str, bytes, os.PathLike]) -> None:
		"""
		Load the Declarative knowledge base.
		"""
		self.df_map_1_1 = pd.read_excel(path, sheet_name='1_1')
		
		self.df_map_2_1 = pd.read_excel(path, sheet_name='2_1')

		self.df_best_before = pd.read_excel(path, sheet_name='best_before')

		self.df_map_max_or = pd.read_excel(path, sheet_name='maximal_or', keep_default_na=False)
		self.df_map_max_or['scale_top'] = self.df_map_max_or.scale_top.where(self.df_map_max_or.scale_top != 'inf', np.inf) # replace 'inf' with np.inf

	def inference_dec(self, df_db: pd.DataFrame) -> pd.DataFrame:
		"""
		Perform inference on the Declarative knowledge base.
		Example:
			df_inferred = inference_dec(df_db, df_map_1_1, df_map_2_1, df_map_max_or)
		Args:
			df_db: dataframe of the database
		Returns:
			df_inferred: dataframe of inferred knowledge
		"""
		joined_1_1 = pd.merge(df_db, self.df_map_1_1, left_on='Condition', right_on='LOINC_Code', how='inner', suffixes=('_db', '_kb'))
		joined_1_1 = joined_1_1[joined_1_1.value_db.between(joined_1_1.scale_low, joined_1_1.scale_top)][['Therapy_Code', 'value_kb']]

		joined_2_1 = pd.merge(pd.merge(self.df_map_2_1, df_db, right_on='Condition', left_on='LOINC_Code_1', how='inner', suffixes=('_kb', '_db_1'), ), 
						df_db, right_on='Condition', left_on='LOINC_Code_2', how='inner', suffixes=('_db_1', '_db_2')).rename(columns={'value': 'value_db_2'})
		joined_2_1 = joined_2_1[joined_2_1.value_db_1.between(joined_2_1.scale_low_1, joined_2_1.scale_top_1) & joined_2_1.value_db_2.between(joined_2_1.scale_low_2, joined_2_1.scale_top_2)][['Therapy_Code', 'value_kb']]

		joined_max_or = pd.merge(df_db, self.df_map_max_or, left_on='Condition', right_on='LOINC_Code', how='inner', suffixes=('_db', '_kb'))
		joined_max_or = joined_max_or[joined_max_or.value_db.between(joined_max_or.scale_low, joined_max_or.scale_top)]
		joined_max_or = joined_max_or.groupby('Therapy_Code')['value_kb'].max().to_frame().reset_index()

		joined_all = pd.concat([joined_1_1, joined_2_1, joined_max_or]).reset_index(drop=True).rename(columns={'Therapy_Code': 'Condition', 'value_kb': 'value'})

		return pd.concat([df_db, joined_all], ignore_index=True)
	

class KB_Prod:
	def __init__(self, path:typing.Union[str, bytes, os.PathLike]=None) -> None:
		if path is not None:
			self.load_kb_prod(path)
		else:
			self.df_map_treatments = pd.DataFrame()
			self.df_map_protocol = pd.DataFrame()
	
	def load_kb_prod(self, path:typing.Union[str, bytes, os.PathLike]) -> None:
		"""
		Load the Procedural knowledge base.
		Example:
			df_map_treatments, df_map_protocol = load_kb_prod()
		Returns:
			df_map_treatments: dataframe of treatments
			df_map_protocol: dataframe of protocol actions
		"""
		self.df_map_treatments = pd.read_excel(path, sheet_name='treatments')
		self.df_map_protocol = pd.read_excel(path, sheet_name='protocol_actions')
	
	def inference_prod(self, df_db_inf:pd.DataFrame) -> pd.Index:
		"""
		Perform inference on the Procedural knowledge base.
		Args:
			df_db_inf (pd.DataFrame): dataframe after the inferred dec knowledge base
		Returns:
			pd.Index: protocol codes that are inferred
		"""
		df_treat_inf = pd.merge(self.df_map_treatments, df_db_inf, left_on=['Therapy_Code', 'Therapy_value'], right_on=['Condition', 'value'], how='left')
		df_treat_inf['bool'] = df_treat_inf['value'].notnull()
		df_treat_inf = df_treat_inf.groupby('protocol_code')['bool'].all()
		df_treat_inf = df_treat_inf[df_treat_inf].index
		return df_treat_inf
	
	def get_protocol(self, protocol_code:pd.Index) -> pd.DataFrame:
		"""
		Get the protocol actions based on the protocol codes.
		Args:
			protocol_code (pd.Index): protocol codes
		Returns:
			pd.DataFrame: dataframe of protocol actions
		"""
		return self.df_map_protocol[self.df_map_protocol['protocol_code'].isin(protocol_code)]
	
class KB:
	def __init__(self, path_dec:typing.Union[str, bytes, os.PathLike]=None, path_prod:typing.Union[str, bytes, os.PathLike]=None) -> None:
		if path_dec is not None:
			self.kb_dec = KB_Dec(path_dec)
		else:
			self.kb_dec = KB_Dec()
		if path_prod is not None:
			self.kb_prod = KB_Prod(path_prod)
		else:
			self.kb_prod = KB_Prod()
	
	def inference_protocol(self, df_db:pd.DataFrame) -> pd.DataFrame:
		"""
		Perform inference on the knowledge base.
		Args:
			df_db (pd.DataFrame): dataframe of the database
		Returns:
			pd.DataFrame: dataframe of the inferred protocol actions
		"""
		df_db_inf = self.kb_dec.inference_dec(df_db)
		protocol_code = self.kb_prod.inference_prod(df_db_inf)
		df_protocol = self.kb_prod.get_protocol(protocol_code)
		return df_protocol
