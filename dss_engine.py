import pandas as pd


class DSS_Engine:
    def __init__(self, db):
        self.db = db
        self.save_db = False

    def retrieval(self, loinc, first_name, last_name, current_date, current_time, component_date, component_time=None):
        # Filter the point of view of the physician
        physician_date = pd.to_datetime(f'{current_date} {current_time}')
        # rel_db = self.db.loc[:physician_date]  # Relevant Database

        # Filter according to the conditions
        target_date = pd.to_datetime(component_date).date()  # Convert target date to date format
        conditions = (self.db['First name'] == first_name) & (self.db['Last name'] == last_name) & \
                     (self.db['LOINC-NUM'] == loinc) & (self.db['Valid start time'].dt.date == target_date) & \
                     (self.db['Transaction time'] < physician_date) & (self.db['Transaction stop time'] > physician_date)

        filtered_df = self.db[conditions]
        filtered_df = self.filter_deleted_rows(filtered_df, current_date, current_time)

        # Check if the time of the component also provided
        if component_time:
            full_date = f'{component_date} {component_time}'
            selected_row = filtered_df[filtered_df['Valid start time'] == full_date]
        else:
            selected_row = filtered_df.sort_values('Valid start time', ascending=False).head(1)

        return selected_row['Value'], selected_row['Unit']

    def history_retrival(self, loinc, first_name, last_name, from_date, from_time, to_date, trans_date, to_time=None, trans_time=None):
        target_date = pd.to_datetime(trans_date).date()
        start = pd.to_datetime(f'{from_date} {from_time}')
        end = pd.to_datetime(to_date).date()

        # Filter according to the conditions
        conditions = (self.db['First name'] == first_name) & (self.db['Last name'] == last_name) & \
                     (self.db['LOINC-NUM'] == loinc) & (self.db['Transaction time'].dt.date == target_date) & \
                     (self.db['Valid start time'].dt >= start) & (self.db['Valid start time'].dt.date <= end)
        filtered_df = self.db[conditions]
        filtered_df = self.filter_deleted_rows(filtered_df, current_date, current_time)

        if trans_time:
            full_date = pd.to_datetime(f'{trans_date} {trans_time}')
            selected_row = filtered_df[filtered_df['Transaction time'] == full_date]
        else:
            selected_row = filtered_df

        if to_time:
            full_end_time = pd.to_datetime(f'{to_date} {to_time}')
            selected_row = filtered_df[filtered_df['Valid start time'] <= full_end_time]

        return selected_row

    def update(self, loinc, first_name, last_name, trans_date, trans_time, component_date, component_time, new_value):
        # Filter according to the conditions
        target_date = pd.to_datetime(f'{component_date} {component_time}')
        conditions = (self.db['First name'] == first_name) & (self.db['Last name'] == last_name) & \
                     (self.db['LOINC-NUM'] == loinc) & (self.db['Transaction time'].dt == target_date)

        filtered_df = self.db[conditions]
        selected_row = filtered_df.sort_values('Transaction time', ascending=False).head(1)

        new_trans = pd.to_datetime(f'{trans_date} {trans_time}')

        new_row = pd.Series([first_name, last_name, loinc, new_value, new_trans,
                             selected_row['Valid start time'], selected_row['Valid stop time'],
                             selected_row['Transaction stop time']], index=self.db.columns)
        self.db = self.db.append(new_row)
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

        trans_stop_date = pd.to_datetime(f'{trans_date} {trans_time}')  # Convert trans stop date to date format
        self.db.at[selected_row.index[0], 'Transaction stop time'] = trans_stop_date
        self.save_db = True

        return selected_row

    @staticmethod
    def filter_deleted_rows(data, trans_date, trans_time):
        # Create a boolean mask to select non-NaN rows in the 'Date' column
        mask = pd.notna(data)

        # Condition: Check if the date is before a certain date (e.g., '2023-01-01') for non-NaN rows
        certain_date = pd.to_datetime(f'{trans_date} {trans_time}')
        condition = data.loc[mask, 'Transaction stop time'] < certain_date

        # Apply the condition to the original DataFrame
        result_df = data.loc[mask & condition]
        return result_df

    def get_patient_data(self):
        group_df = self.db.groupby(['ID', 'LOINC-NUM'])
        last_patient_data = group_df.apply(lambda x: x.sort_values("Valid start time", ascending=False).head(1))
        return last_patient_data

    def save(self, db_path):
        if self.save_db:
            self.db.to_csv(db_path, index=False)
            self.save_db = False
            return 'Database Saved!'
        return 'No Changes to Save!'


db_path = 'project_db.csv'
df = pd.read_csv(db_path,
                 parse_dates=['Valid start time', 'Valid stop time', 'Transaction time', 'Transaction stop time'])
dss = DSS_Engine(db=df)

# dss.get_patient_data()

# dss.retrieval(loinc='14743-9',
#               first_name='Yonathan',
#               last_name='Spoon',
#               current_date='2018-7-1', current_time='11:00',
#               component_date='2018-5-17', component_time='19:00')

# dss.delete(loinc='14743-9',
#            first_name='Yonathan',
#            last_name='Spoon',
#            trans_date='2018-6-30', trans_time='11:00',
#            component_date='2018-5-17', component_time='19:00')

dss.save(db_path)
