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
			self.df_loinc = pd.DataFrame()
			self.df_states = pd.DataFrame()
	
	def load_kb_dec(self, path:typing.Union[str, bytes, os.PathLike]) -> None:
		"""
		Load the Declarative knowledge base.
		"""
		self.df_map_1_1 = pd.read_excel(path, sheet_name='1_1')
		
		self.df_map_2_1 = pd.read_excel(path, sheet_name='2_1')

		self.df_best_before = pd.read_excel(path, sheet_name='best_before')

		self.df_map_max_or = pd.read_excel(path, sheet_name='maximal_or', keep_default_na=False)
		self.df_map_max_or['scale_top'] = self.df_map_max_or.scale_top.where(self.df_map_max_or.scale_top != 'inf', np.inf) # replace 'inf' with np.inf

		self.df_loinc = pd.read_excel(path, sheet_name='LOINC')

		self.df_states = pd.read_excel(path, sheet_name='states')

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
		df_db['Value'] = pd.to_numeric(df_db['Value'],errors='coerce').fillna(df_db['Value']).tolist()
		joined_1_1 = pd.merge(df_db, self.df_map_1_1, left_on='LOINC-NUM', right_on='LOINC-NUM', how='inner', suffixes=('_db', '_kb'))
		joined_1_1 = joined_1_1[joined_1_1.Value_db.between(joined_1_1.scale_low, joined_1_1.scale_top)][['Therapy_Code', 'Value_kb']]

		joined_2_1 = pd.merge(pd.merge(self.df_map_2_1, df_db, right_on='LOINC-NUM', left_on='LOINC-NUM_1', how='inner', suffixes=('_kb', '_db_1'), ), 
						df_db, right_on='LOINC-NUM', left_on='LOINC-NUM_2', how='inner', suffixes=('_db_1', '_db_2')).rename(columns={'Value': 'Value_db_2'})
		joined_2_1 = joined_2_1[joined_2_1.Value_db_1.between(joined_2_1.scale_low_1, joined_2_1.scale_top_1) & 
			  					joined_2_1.Value_db_2.between(joined_2_1.scale_low_2, joined_2_1.scale_top_2)][['Therapy_Code', 'Value_kb']]

		joined_max_or = pd.merge(df_db, self.df_map_max_or, left_on='LOINC-NUM', right_on='LOINC-NUM', how='inner', suffixes=('_db', '_kb'))
		joined_max_or = joined_max_or[joined_max_or.Value_db.between(joined_max_or.scale_low, joined_max_or.scale_top)]
		joined_max_or = joined_max_or.groupby('Therapy_Code')['Value_kb'].max().to_frame().reset_index()

		joined_all = pd.concat([joined_1_1, joined_2_1, joined_max_or]).reset_index(drop=True).rename(columns={'Therapy_Code': 'LOINC-NUM', 'Value_kb': 'Value'})

		return pd.concat([df_db, joined_all], ignore_index=True)
	
	def get_best_before(self, loinc_num:str) -> (pd.Timedelta, pd.Timedelta):
		"""
		Get the best before date of the database.
		Args:
			loinc_num (str): LOINC-NUM
		Returns:
			pd.Timedelta: Timedelta with the best before date
			pd.Timedelta: Timedelta with the best after date
		"""
		df = self.df_best_before[self.df_best_before['LOINC-NUM'] == loinc_num]
		return pd.Timedelta(f"{df['good_before_value'].item()} {df['good_before_time_unit'].item()}"), pd.Timedelta(f"{df['good_after_value'].item()} {df['good_after_time_unit'].item()}")
	
	def get_loinc_desc(self, loinc_num:str) -> str:
		"""
		Get the LOINC description.
		Args:
			loinc_num (str): LOINC-NUM

		Returns:
			str: LOINC description
		"""
		return self.df_loinc[self.df_loinc['LOINC-NUM'] == loinc_num]['LONG_COMMON_NAME'].item()
	
	def get_full_loinc_desc(self) -> pd.DataFrame:
		"""
		Get the full LOINC description.
		Returns:
			pd.DataFrame: dataframe of LOINC description
		"""
		return self.df_loinc[['LOINC-NUM', 'LONG_COMMON_NAME']]
	
	def get_full_states(self) -> pd.DataFrame:
		"""
		Get the full states.
		Returns:
			pd.DataFrame: dataframe of states
		"""
		return self.df_states
	
	def get_states(self, therapy_code:str) -> str:
		"""
		Get the states of the Therapy_Code.
		Args:
			therapy_code (str): Therapy_Code
		Returns:
			str: state description
		"""
		return self.df_states[self.df_states['Therapy_Code'] == therapy_code]['Therapy_desc'].item()
	

class KB_Proc:
	def __init__(self, path:typing.Union[str, bytes, os.PathLike]=None) -> None:
		if path is not None:
			self.load_kb_proc(path)
		else:
			self.df_map_treatments = pd.DataFrame()
			self.df_map_protocol = pd.DataFrame()
	
	def load_kb_proc(self, path:typing.Union[str, bytes, os.PathLike]) -> None:
		"""
		Load the Procedural knowledge base.
		Example:
			df_map_treatments, df_map_protocol = load_kb_proc()
		Returns:
			df_map_treatments: dataframe of treatments
			df_map_protocol: dataframe of protocol actions
		"""
		self.df_map_treatments = pd.read_excel(path, sheet_name='treatments')
		self.df_map_protocol = pd.read_excel(path, sheet_name='protocol_actions')
	
	def inference_proc(self, df_db_inf:pd.DataFrame) -> pd.Index:
		"""
		Perform inference on the Procedural knowledge base.
		Args:
			df_db_inf (pd.DataFrame): dataframe after the inferred dec knowledge base
		Returns:
			pd.Index: protocol codes that are inferred
		"""
		df_treat_inf = pd.merge(self.df_map_treatments, df_db_inf, left_on=['Therapy_Code', 'Therapy_Value'], right_on=['LOINC-NUM', 'Value'], how='left')
		df_treat_inf['bool'] = df_treat_inf['Value'].notnull()
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
			self.kb_proc = KB_Proc(path_prod)
		else:
			self.kb_proc = KB_Proc()
	
	def inference_protocol(self, df_db:pd.DataFrame) -> pd.DataFrame:
		"""
		Perform inference on the knowledge base.
		Args:
			df_db (pd.DataFrame): dataframe of the database
		Returns:
			pd.DataFrame: dataframe of the inferred protocol actions
		"""
		df_db_inf = self.kb_dec.inference_dec(df_db)
		protocol_code = self.kb_proc.inference_proc(df_db_inf)
		df_protocol = self.kb_proc.get_protocol(protocol_code)
		return df_protocol
