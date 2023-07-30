import pandas as pd
from KnowledgeBase import KB


class DSS_Engine:
    def __init__(self, db):
        self.db = db
        self.save_db = False
        self.kb = KB('kb_dec.xlsx', 'kb_proc.xlsx')
        self.db.insert(4,'LOINC-NAME', self.db['LOINC-NUM'].map(dict(self.kb.kb_dec.get_full_loinc_desc().values)))


    def retrieval(self, loinc, first_name, last_name, current_date, current_time, component_date, component_time=None):
        # Filter the point of view of the physician
        physician_date = pd.to_datetime(f'{current_date} {current_time}')
        # rel_db = self.db.loc[:physician_date]  # Relevant Database

        # Filter according to the conditions
        target_date = pd.to_datetime(component_date).date()  # Convert target date to date format
        conditions = (self.db['First name'] == first_name) & (self.db['Last name'] == last_name) & \
                     (self.db['LOINC-NUM'] == loinc) & (self.db['Valid start time'].dt.date == target_date) & \
                     (self.db['Transaction time'] < physician_date)

        filtered_df = self.db[conditions]
        filtered_df = self.filter_deleted_rows(filtered_df, current_date, current_time)

        # Check if the time of the component also provided
        if component_time:
            full_date = f'{component_date} {component_time}'
            selected_row = filtered_df[filtered_df['Valid start time'] == full_date]
        else:
            selected_row = filtered_df.sort_values('Valid start time', ascending=False).head(1)

        selected_row = self.filter_best_before(selected_row, current_date, current_time)
        return selected_row['Value'], selected_row['Unit'], selected_row['Valid']

    def history_retrival(self, loinc, first_name, last_name, from_date, from_time, to_date, trans_date, to_time=None,
                         trans_time=None):
        target_date = pd.to_datetime(trans_date).date()
        start = pd.to_datetime(f'{from_date} {from_time}')
        end = pd.to_datetime(to_date).date()

        # Filter according to the conditions
        conditions = (self.db['First name'] == first_name) & (self.db['Last name'] == last_name) & \
                     (self.db['LOINC-NUM'] == loinc) & (self.db['Transaction time'].dt.date <= target_date) & \
                     (self.db['Valid start time'] >= start) & (self.db['Valid start time'].dt.date <= end)
        filtered_df = self.db[conditions]

        if trans_time:
            filtered_df = self.filter_deleted_rows(filtered_df, trans_date, trans_time)
            full_date = pd.to_datetime(f'{trans_date} {trans_time}')
            selected_row = filtered_df[filtered_df['Transaction time'] <= full_date]
        else:
            current_time = '00:00'
            filtered_df = self.filter_deleted_rows(filtered_df, trans_date, current_time)
            selected_row = filtered_df

        if to_time:
            full_end_time = pd.to_datetime(f'{to_date} {to_time}')
            selected_row = filtered_df[filtered_df['Valid start time'] == full_end_time]

        if trans_time:
            selected_row = self.filter_best_before(selected_row, trans_date, trans_time)
        else:
            selected_row = self.filter_best_before(selected_row, trans_date, current_time)
        return selected_row

    def update(self, loinc, first_name, last_name, trans_date, trans_time, component_date, component_time, new_value):
        # Filter according to the conditions
        target_date = pd.to_datetime(f'{component_date} {component_time}')
        conditions = (self.db['First name'] == first_name) & (self.db['Last name'] == last_name) & \
                     (self.db['LOINC-NUM'] == loinc) & (self.db['Valid start time'] == target_date)

        filtered_df = self.db[conditions]
        filtered_df = self.filter_deleted_rows(filtered_df, trans_date, trans_time)

        selected_row = filtered_df.sort_values('Transaction time', ascending=False).head(1)

        new_trans = pd.to_datetime(f'{trans_date} {trans_time}')
        if len(selected_row) == 0:
            return -1, -1
        
        new_row = pd.Series([selected_row['ID'].values[0], first_name, last_name, loinc, new_value,
                             selected_row['Unit'].values[0], new_trans, selected_row['Valid start time'].values[0],
                             selected_row['Valid stop time'].values[0],
                             selected_row['Transaction stop time'].values[0]], index=self.db.columns)
        self.db = self.db.append(new_row, ignore_index=True)
        self.save_db = True
        return selected_row, new_row

    def delete(self, loinc, first_name, last_name, trans_date, trans_time, component_date, component_time):
        # Add 'Transaction Stop Time' When the there is a deletion
        target_date = pd.to_datetime(component_date).date()  # Convert target date to date format
        conditions = (self.db['First name'] == first_name) & (self.db['Last name'] == last_name) & \
                     (self.db['LOINC-NUM'] == loinc) & (self.db['Valid start time'].dt.date == target_date)

        filtered_df = self.db[conditions]

        # Check if the time of the component also provided
        if component_time:
            full_date = f'{component_date} {component_time}'
            selected_row = filtered_df[filtered_df['Valid start time'] == full_date]
        else:
            selected_row = filtered_df.sort_values('Valid start time', ascending=False).head(1)
        
        if len(selected_row) == 0:
            return -1

        trans_stop_date = pd.to_datetime(f'{trans_date} {trans_time}')  # Convert trans stop date to date format
        self.db.at[selected_row.index[0], 'Transaction stop time'] = trans_stop_date
        self.save_db = True

        return selected_row

    @staticmethod
    def filter_deleted_rows(data, trans_date, trans_time):
        mask = pd.isnull(data['Transaction stop time'])
        certain_date = pd.to_datetime(f'{trans_date} {trans_time}')
        condition = certain_date < data['Transaction stop time']

        # Apply the condition to the original DataFrame
        result_df = data.loc[mask + condition]
        return result_df

    def filter_best_before(self, data, current_date, current_time):
        data['Valid'] = None
        if len(data) == 0:
            return data

        current = pd.to_datetime(f'{current_date} {current_time}')

        def func(row):
            time_delta = self.kb.kb_dec.get_best_before(row['LOINC-NUM'])
            if (row['Valid start time'] - time_delta[0]) <= current <= (row['Valid start time'] + time_delta[0]):
                return True
            return False

        data['Valid'] = data.apply(func, axis=1)
        return data

    def get_patient_data(self, trans_date, trans_time):
        certain_date = pd.to_datetime(f'{trans_date} {trans_time}')

        condition = (self.db['Transaction time'] <= certain_date)
        filtered_df = self.db[condition]
        filtered_df = self.filter_deleted_rows(filtered_df, trans_date, trans_time)

        group_df = filtered_df.groupby(['ID', 'LOINC-NUM'], as_index=False)
        last_patient_data = group_df.apply(lambda x: x.sort_values(["Valid start time", "Transaction time"],
                                                                   ascending=[False, False]).head(1))
        return last_patient_data

    def get_states(self, trans_date='2018-5-22', trans_time='11:30'):
        patient_data = self.get_patient_data(trans_date=trans_date, trans_time=trans_time)
        return patient_data.groupby('ID').apply(self.kb.inference_protocol)

    def save(self, db_path):
        if self.save_db:
            self.db.to_csv(db_path, index=False)
            self.save_db = False
            return 'Database Saved!'
        return 'No Changes to Save!'


db_path = 'project_db_updated.csv'
df = pd.read_csv(db_path,
                 parse_dates=['Valid start time', 'Valid stop time', 'Transaction time', 'Transaction stop time'])
dss = DSS_Engine(db=df)

# # pat_df = dss.get_patient_data()
#
# a = dss.get_states(trans_date='2018-5-22', trans_time='11:30')
#
# print(a)

# dss.retrieval(loinc='30313-1',
#               first_name='Avraham',
#               last_name='Avraham',
#               current_date='2018-5-22', current_time='11:00',
#               component_date='2018-5-21', component_time='15:00')

# dss.history_retrival(loinc='30313-1',
#                      first_name='Avraham',
#                      last_name='Avraham',
#                      from_date='2018-5-21', from_time='9:00',
#                      to_date='2018-5-22',
#                      trans_date='2018-5-23', trans_time='18:00')

# dss.update(loinc='30313-1',
#            first_name='Avraham',
#            last_name='Avraham',
#            trans_date='2018-5-25', trans_time='15:00',
#            component_date='2018-5-23', component_time='15:00', new_value=15.5)

# dss.delete(loinc='14743-9',
#            first_name='Yonathan',
#            last_name='Spoon',
#            trans_date='2018-6-30', trans_time='11:00',
#            component_date='2018-5-17', component_time='19:00')

dss.save(db_path)
