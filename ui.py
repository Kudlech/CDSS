
import pandas as pd
import io
import numpy as np
import datetime
import streamlit as st
from dss_engine import DSS_Engine
from KnowledgeBase import KB


class UI():
    def __init__(self, db_path='project_db.csv', debug_mode=False) -> None:
        self.debug_mode = debug_mode

        self.db_path = db_path
        # self.path_dec = path_dec
        # self.path_prod = path_prod
        
        # read db
        df = pd.read_csv(
            filepath_or_buffer=self.db_path,
            parse_dates=['Valid start time', 'Valid stop time', 'Transaction time', 'Transaction stop time']
            )
        
        # init engine
        self.cds = DSS_Engine(db=df.copy())
        del(df)

        self.state_code_to_name = dict(pd.read_excel('state_code_to_name.xlsx').values)

        # [UI] create transaction (current) time picker
        self.col_transaction_date_picker, self.col_transaction_time_picker, _, _  = st.columns(4)  
        with self.col_transaction_date_picker:
            self.date_current = st.date_input(
                "📅 Current date: ",
                (datetime.date(
                day=self.cds.db['Transaction time'].max().day, 
                month=self.cds.db['Transaction time'].max().month, 
                year=self.cds.db['Transaction time'].max().year,
                )), format='DD/MM/YYYY',
            ) 
            if self.debug_mode: st.write(self.date_current)

        with self.col_transaction_time_picker:
            self.time_current = st.time_input('🕒 Current time:  ', datetime.time(
                hour=self.cds.db['Transaction time'].max().hour, 
                minute=self.cds.db['Transaction time'].max().minute
                ),
                step=600,
            )
            if self.debug_mode: st.write(self.time_current)

        # [UI] create sidebar
        self.page_names_to_funcs = {
            "🖥️ Monitor": self.page_home,
            "📝 Actions": self.page_tabs,
        }        

        demo_name = st.sidebar.radio("Choose a page", self.page_names_to_funcs.keys())
        self.page_names_to_funcs[demo_name]()

    def page_home(self):
        _df = self.cds.db.copy()
        _df['Full name'] = _df['First name'] + ' ' + _df['Last name']
        patient_full_name_list = list(_df.drop_duplicates(['ID', 'First name', 'Last name'])['Full name'])

        no_patient_selected_placeholder_str = '---'
        col_patient_selction, col_state_display, _ = st.columns([1,1,4])

        with col_patient_selction:        
            selected_patient = st.selectbox('Patient name:    ', [no_patient_selected_placeholder_str] + patient_full_name_list)

        
        trans_date=f'{self.date_current}'
        trans_time=f'{self.time_current.hour}:{self.time_current.minute}'
        patient_data = self.cds.get_patient_data(trans_date=trans_date, trans_time=trans_time)
        
        # st.dataframe(patient_data)
        df_treatments = self.cds.get_states(trans_date=trans_date, trans_time=trans_time).reset_index()
        # st.dataframe(df_treatments)
        if selected_patient == no_patient_selected_placeholder_str:

            for patient_full_name in patient_full_name_list:
                # st.write('🌡️ **Patient states:**')
                patient_id = list(set(_df[_df['Full name'].eq(patient_full_name)]['ID']))[0]
                df_db_inf = self.cds.kb.kb_dec.inference_dec(patient_data[patient_data.ID.eq(patient_id)][['LOINC-NUM', 'Value']])
                df_db_inf['State type'] = df_db_inf.Therapy_Code.apply(lambda x: self.cds.kb.kb_dec.get_states(x))
                df_db_inf['Value'] = df_db_inf.Value.map(self.state_code_to_name)
                for state_type in set(df_db_inf['State type']):
                    try:
                        state_value = list(df_db_inf[df_db_inf['State type'].eq(state_type)]['Value'])[0]
                        
                    except:
                        state_value = None
                    patient_data.loc[patient_data.ID.eq(patient_id), state_type] = state_value
                # st.dataframe(df_db_inf[['State type', 'Value']])    
            # step = 3
            # for idx_row in range(0, len(patient_full_name_list), step):
            #     cols = st.columns(step)
            #     for idx_col, patient_col in enumerate(cols):
            #         with patient_col:
            #             if len(patient_full_name_list) <= idx_row+idx_col:
            #                 continue
            #             patient_full_name = patient_full_name_list[idx_row+idx_col] 
            #             st.write(patient_full_name)
            #             patient_id = list(set(_df[_df['Full name'].eq(patient_full_name)]['ID']))[0]
            #             st.write(patient_id)

            #             st.write('🌡️ **Patient states:**')
            #             df_db_inf = self.cds.kb.kb_dec.inference_dec(patient_data[patient_data.ID.eq(patient_id)][['LOINC-NUM', 'Value']])
            #             df_db_inf['State type'] = df_db_inf.Therapy_Code.apply(lambda x: self.cds.kb.kb_dec.get_states(x))
            #             df_db_inf['Value'] = df_db_inf.Value.map(self.state_code_to_name)
            #             # st.dataframe(df_db_inf[['State type', 'Value']])
            #             for _, row in df_db_inf[['State type', 'Value']].iterrows():
            #                 st.write(f'{row["State type"]}: {row["Value"]}')

            #             st.write('💊 **Patient treatments:**')
            #             st.dataframe(df_treatments[df_treatments['ID'].eq(patient_id)], hide_index=True)

            # st.write('States:')
            # df_db_inf = self.cds.kb.kb_dec.inference_dec(patient_data[['LOINC-NUM', 'Value']])
            # df_db_inf['State type'] = df_db_inf.Therapy_Code.apply(lambda x: self.cds.kb.kb_dec.get_states(x))
            # st.dataframe(df_db_inf)

            # st.write('Treatments:')
            # st.dataframe(df_treatments, hide_index=True)

            # st.metric('Number of patients:', len(patient_data[~patient_data['LOINC-NUM'].eq('Gender')].drop_duplicates('ID')))
            

            st.write('🌡️ Patient states:')
            st.dataframe(patient_data[~patient_data['LOINC-NUM'].eq('Gender')].drop_duplicates('ID')[['ID', 'First name', 'Last name'] + list(set(df_db_inf['State type']))], hide_index=True)
        else:
            selected_patient_id = list(set(_df[_df['Full name'].eq(selected_patient)]['ID']))[0]

            
            st.write('🌡️ Patient states:')
            df_db_inf = self.cds.kb.kb_dec.inference_dec(patient_data[patient_data.ID.eq(selected_patient_id)][['LOINC-NUM', 'Value']])
            df_db_inf['State type'] = df_db_inf.Therapy_Code.apply(lambda x: self.cds.kb.kb_dec.get_states(x))
            df_db_inf['Value'] = df_db_inf.Value.map(self.state_code_to_name)
            st.dataframe(df_db_inf[['State type', 'Value']])

            st.write('💊 Patient treatments:')
            st.dataframe(df_treatments[df_treatments['ID'].eq(selected_patient_id)], hide_index=True)

            st.write('📂 Patient history:')
            st.dataframe(patient_data[
                ~(patient_data['LOINC-NUM'].eq('Gender')) 
                & (patient_data['ID'].eq(selected_patient_id))], 
                hide_index=True)
            with col_state_display:
                # st.write('Patient state:')
                # st.write('[PLACEHOLDER]')
                pass

    def page_tabs(self):
        tab_retrieve, tab_history, tab_update, tab_delete = st.tabs(["⬇️ Retrieve", "🗒️ History", "🖊️ Update", "❌ Delete"])

        with tab_retrieve:
            self.page_retrieve()

        with tab_history:
            self.page_history()

        with tab_update:
            self.page_update()

        with tab_delete:
            self.page_delete()

    def page_history(self):
        col_patient_selection, col_loinc_selection, _, col_to_valid_time_disabler = st.columns(4)
        col_from_valid_date_picker, col_from_valid_time_picker, col_to_valid_date_picker, col_to_valid_time_picker = st.columns(4)  

        with col_loinc_selection:
            _df = self.cds.db.copy()
            loinc_num_full_list = list(_df.drop_duplicates(['LOINC-NUM'])['LOINC-NUM'])
            selected_loinc = st.selectbox('LOINC-NUM:  ', loinc_num_full_list)
            if self.debug_mode: st.write(selected_loinc)
        
        with col_patient_selection:
            _df = self.cds.db.copy()
            _df['Full name'] = _df['First name'] + ' ' + _df['Last name']
            patient_full_name_list = list(_df.drop_duplicates(['ID', 'First name', 'Last name'])['Full name'])
            selected_patient = st.selectbox('Patient name: ', patient_full_name_list)
            if self.debug_mode: st.write(selected_patient)

        with col_from_valid_date_picker:
            date_from_valid = st.date_input(
                "From valid date:",
                (datetime.date(
                day=self.cds.db['Valid start time'].min().day, 
                month=self.cds.db['Valid start time'].min().month, 
                year=self.cds.db['Valid start time'].min().year
                )), format='DD/MM/YYYY',
            ) 
            if self.debug_mode: st.write(date_from_valid)

        with col_to_valid_date_picker:
            date_to_valid = st.date_input(
                "To valid date:",
                (datetime.date(
                day=self.cds.db['Valid start time'].max().day, 
                month=self.cds.db['Valid start time'].max().month, 
                year=self.cds.db['Valid start time'].max().year
                )), format='DD/MM/YYYY',
            ) 
            if self.debug_mode: st.write(date_to_valid)

        # with col_from_valid_time_disabler:
        #     button_from_valid_time_disabler = st.checkbox('Use "From valid time"', value=False)
        with col_to_valid_time_disabler:
            button_to_valid_time_disabler = st.checkbox('Use "To valid time"', value=False)

        with col_from_valid_time_picker:
            time_from_valid = st.time_input('From valid time', datetime.time(hour=self.cds.db['Valid start time'].min().hour, 
                                                                             minute=self.cds.db['Valid start time'].min().minute), 
                                                                             step=600,
                                                                            #  disabled=(not button_from_valid_time_disabler),
                                                                             )
            # time_from_valid_value = time_from_valid if button_from_valid_time_disabler else None
            time_from_valid_value = time_from_valid
            if self.debug_mode: st.write(time_from_valid_value)

        with col_to_valid_time_picker:
            time_to_valid = st.time_input('To valid time', datetime.time(hour=self.cds.db['Valid start time'].max().hour, 
                                                                         minute=self.cds.db['Valid start time'].max().minute), 
                                                                         disabled=(not button_to_valid_time_disabler),
                                                                         step=600,
                                                                         )
            time_to_valid_value = time_to_valid if button_to_valid_time_disabler else None
            if self.debug_mode: st.write(time_to_valid_value)

        patient_histroy_data = self.cds.history_retrival(
            loinc=selected_loinc, 
            first_name=selected_patient.split()[0], 
            last_name=selected_patient.split()[1], 

            trans_date=f'{self.date_current}', 
            trans_time=f'{self.time_current.hour}:{self.time_current.minute}',

            from_date=f'{date_from_valid}', 
            from_time=None if time_from_valid_value == None else f'{time_from_valid_value.hour}:{time_from_valid_value.minute}',

            to_date=f'{date_to_valid}', 
            to_time=None if time_to_valid_value == None else f'{time_to_valid_value.hour}:{time_to_valid_value.minute}',
            )
        st.write('Retrieved history:')
        st.dataframe(patient_histroy_data, hide_index=True)

    def page_update(self):
        col_inputs_left, col_new_loinc_value = st.columns([3,1])

        with col_inputs_left:
            col_patient_selection, col_loinc_selection, _ = st.columns(3)
            col_valid_date_picker, col_valid_time_picker, _, = st.columns(3)
            
            with col_loinc_selection:
                _df = self.cds.db.copy()
                loinc_num_full_list = list(_df.drop_duplicates(['LOINC-NUM'])['LOINC-NUM'])
                selected_loinc = st.selectbox('LOINC-NUM:', loinc_num_full_list)
                selected_loinc
                if self.debug_mode: st.write(selected_loinc)
                        
            with col_patient_selection:
                _df = self.cds.db.copy()
                _df['Full name'] = _df['First name'] + ' ' + _df['Last name']
                patient_full_name_list = list(_df.drop_duplicates(['ID', 'First name', 'Last name'])['Full name'])
                selected_patient = st.selectbox('Patient name:     ', patient_full_name_list)
                if self.debug_mode: st.write(selected_patient)

            with col_valid_date_picker:
                date_valid = st.date_input(
                    "Valid date:",
                    (datetime.date(
                    day=self.cds.db['Valid start time'].max().day, 
                    month=self.cds.db['Valid start time'].max().month, 
                    year=self.cds.db['Valid start time'].max().year
                    )), format='DD/MM/YYYY',
                ) 
                if self.debug_mode: st.write(date_valid)

            with col_valid_time_picker:
                time_valid = st.time_input('Valid time: ', datetime.time(hour=self.cds.db['Valid start time'].max().hour, minute=self.cds.db['Valid start time'].max().minute), 
                                        #    disabled=(not button_valid_time_disabler),
                                        step=600,
                                        )
                time_valid_value = time_valid# if button_valid_time_disabler else None
                if self.debug_mode: st.write(time_valid_value)

        with col_new_loinc_value:
                col_0, col_1 = st.columns(2)  
                form = st.form('New LOINC value form')
                with col_0:
                    text_input_new_loinc_value = form.text_input('New value')
                with col_1:
                    button_submitted = form.form_submit_button(label="Submit")                   

        if button_submitted:
            selected_row, new_row = self.cds.update(
                        loinc=selected_loinc, 
                        first_name=selected_patient.split()[0], 
                        last_name=selected_patient.split()[1], 
                        trans_date=f'{self.date_current}', 
                        trans_time=f'{self.time_current.hour}:{self.time_current.minute}', 
                        component_date=f'{date_valid}', 
                        component_time=None if time_valid_value == None else f'{time_valid_value.hour}:{time_valid_value.minute}',
                        new_value=text_input_new_loinc_value,
                        )
            if type(selected_row) == int and selected_row == -1:
                st.error('Data does not exist', icon="🚨")
            else:
                self.cds.save(self.db_path)
                st.write('Selected row:')
                st.write(selected_row, hide_index=True)
                st.write('New row:')
                st.write(new_row, hide_index=True)

        max_valid_datetime = self.cds.db['Valid start time'].max()
        max_valid_date = datetime.date(day=  max_valid_datetime.day,  month=  max_valid_datetime.month, year= max_valid_datetime.year)
        max_valid_time = datetime.time(hour= max_valid_datetime.hour, minute= max_valid_datetime.minute)

        min_valid_datetime = self.cds.db['Valid start time'].min()
        min_valid_date = datetime.date(day=  min_valid_datetime.day,  month=  min_valid_datetime.month, year= min_valid_datetime.year)
        min_valid_time = datetime.time(hour= min_valid_datetime.hour, minute= min_valid_datetime.minute)
        
        patient_histroy_data = self.cds.history_retrival(
        loinc=selected_loinc, 
        first_name=selected_patient.split()[0], 
        last_name=selected_patient.split()[1], 

        trans_date=f'{self.date_current}', 
        trans_time=f'{self.time_current.hour}:{self.time_current.minute}',

        from_date=f'{min_valid_date}', 
        from_time=f'{min_valid_time.hour}:{min_valid_time.minute}',

        to_date=f'{max_valid_date}', 
        to_time=f'{max_valid_time.hour}:{max_valid_time.minute}',
        )
        st.write('Retrieved history:')
        st.dataframe(patient_histroy_data, hide_index=True)

    def page_delete(self):
        col_patient_selection, col_loinc_selection,  _, _= st.columns(4)
        col_valid_date_picker, col_valid_time_picker, _, col_delete = st.columns(4)  
        
        with col_loinc_selection:
            _df = self.cds.db.copy()
            loinc_num_full_list = list(_df.drop_duplicates(['LOINC-NUM'])['LOINC-NUM'])
            selected_loinc = st.selectbox('LOINC-NUM: ', loinc_num_full_list)
            if self.debug_mode: st.write(selected_loinc)
                    
        with col_patient_selection:
            _df = self.cds.db.copy()
            _df['Full name'] = _df['First name'] + ' ' + _df['Last name']
            patient_full_name_list = list(_df.drop_duplicates(['ID', 'First name', 'Last name'])['Full name'])
            selected_patient = st.selectbox('Patient name:', patient_full_name_list)
            if self.debug_mode: st.write(selected_patient)

        with col_valid_date_picker:
            date_valid = st.date_input(
                "Valid date: ",
                (datetime.date(
                day=self.cds.db['Valid start time'].max().day, 
                month=self.cds.db['Valid start time'].max().month, 
                year=self.cds.db['Valid start time'].max().year
                )), format='DD/MM/YYYY',
            ) 
            if self.debug_mode: st.write(date_valid)

        with col_valid_time_picker:
            time_valid = st.time_input('Valid time:', datetime.time(hour=self.cds.db['Valid start time'].max().hour, minute=self.cds.db['Valid start time'].max().minute), 
                                       step=600,
                                    #    disabled=(not button_valid_time_disabler),
                                       )
            time_valid_value = time_valid# if button_valid_time_disabler else None
            if self.debug_mode: st.write(time_valid_value)

        with col_delete:       
                st.write('')
                st.write('')
                button_delete = st.button('Delete')  

        if button_delete:
            selected_row = self.cds.delete(
                        loinc=selected_loinc, 
                        first_name=selected_patient.split()[0], 
                        last_name=selected_patient.split()[1], 
                        trans_date=f'{self.date_current}', 
                        trans_time=f'{self.time_current.hour}:{self.time_current.minute}', 
                        component_date=f'{date_valid}', 
                        component_time=None if time_valid_value == None else f'{time_valid_value.hour}:{time_valid_value.minute}'
                        )
            if type(selected_row) == int and selected_row == -1: 
                st.error('Data does not exist', icon="🚨")
            else:
                self.cds.save(self.db_path)
                st.write('Deleted row:')
                st.dataframe(selected_row, hide_index=True)
                
        

        max_valid_datetime = self.cds.db['Valid start time'].max()
        max_valid_date = datetime.date(day=  max_valid_datetime.day,  month=  max_valid_datetime.month, year= max_valid_datetime.year)
        max_valid_time = datetime.time(hour= max_valid_datetime.hour, minute= max_valid_datetime.minute)

        min_valid_datetime = self.cds.db['Valid start time'].min()
        min_valid_date = datetime.date(day=  min_valid_datetime.day,  month=  min_valid_datetime.month, year= min_valid_datetime.year)
        min_valid_time = datetime.time(hour= min_valid_datetime.hour, minute= min_valid_datetime.minute)
        
        patient_histroy_data = self.cds.history_retrival(
        loinc=selected_loinc, 
        first_name=selected_patient.split()[0], 
        last_name=selected_patient.split()[1], 

        trans_date=f'{self.date_current}', 
        trans_time=f'{self.time_current.hour}:{self.time_current.minute}',

        from_date=f'{min_valid_date}', 
        from_time=f'{min_valid_time.hour}:{min_valid_time.minute}',

        to_date=f'{max_valid_date}', 
        to_time=f'{max_valid_time.hour}:{max_valid_time.minute}',
        )
        st.write('Retrieved history:')
        st.dataframe(patient_histroy_data, hide_index=True)
          
    def page_retrieve(self):
        col_patient_selection, col_loinc_selection, _, _ = st.columns(4)
        col_valid_date_picker, col_valid_time_picker, col_valid_time_disabler, _ = st.columns(4)  

        with col_loinc_selection:
            _df = self.cds.db.copy()
            loinc_num_full_list = list(_df.drop_duplicates(['LOINC-NUM'])['LOINC-NUM'])
            selected_loinc = st.selectbox('LOINC-NUM:   ', loinc_num_full_list)
            if self.debug_mode: st.write(selected_loinc)
              
        
        with col_patient_selection:
            _df = self.cds.db.copy()
            _df['Full name'] = _df['First name'] + ' ' + _df['Last name']
            patient_full_name_list = list(_df.drop_duplicates(['ID', 'First name', 'Last name'])['Full name'])
            selected_patient = st.selectbox('Patient name:  ', patient_full_name_list)
            if self.debug_mode: st.write(selected_patient)

        with col_valid_date_picker:
            date_valid = st.date_input(
                "Valid date:  ",
                (datetime.date(
                day=self.cds.db['Valid start time'].max().day, 
                month=self.cds.db['Valid start time'].max().month, 
                year=self.cds.db['Valid start time'].max().year
                )), format='DD/MM/YYYY',
            ) 
            if self.debug_mode: st.write(date_valid)

        with col_valid_time_disabler:
            st.write('')
            st.write('')
            button_valid_time_disabler = st.checkbox('Use valid time ', value=False)

        with col_valid_time_picker:
            time_valid = st.time_input('Valid time:  ', 
                                       datetime.time(hour=self.cds.db['Valid start time'].max().hour, minute=self.cds.db['Valid start time'].max().minute), 
                                       step=600,
                                       disabled=(not button_valid_time_disabler))
            time_valid_value = time_valid if button_valid_time_disabler else None
            if self.debug_mode: st.write(time_valid_value)


        # trans_date=f'{d}', trans_time=f'{t.hour}:{t.minute}'
        patient_data = self.cds.retrieval(
            loinc=selected_loinc, 
            first_name=selected_patient.split()[0], 
            last_name=selected_patient.split()[1], 
            current_date=f'{self.date_current}', 
            current_time=f'{self.time_current.hour}:{self.time_current.minute}', 
            component_date=f'{date_valid}', 
            component_time=None if time_valid_value == None else f'{time_valid_value.hour}:{time_valid_value.minute}')
        
        st.write('Retrieved data:')
        st.dataframe(patient_data, hide_index=False)



        # patient_df = df.groupby(['First name', 'Last name', 'LOINC-NUM', 'Unit'])['Value'].apply(list).reset_index()
        # patient_df = patient_df[patient_df['Unit'] != 'none']
        
        # st.dataframe(
        #     patient_df, 
        #     hide_index=True, 
        #     column_config={
        #         "Value": st.column_config.LineChartColumn("Values (past 30 days)", y_min=0, y_max=100)
        #         },
        #     )


        # st.column_config.LineChartColumn(label=None, *, width=None, help=None, y_min=None, y_max=None)


        
    # def retrieve_db(self):
    #     df = pd.read_csv(
    #         filepath_or_buffer=self.db_path,
    #         parse_dates=['Valid start time', 'Valid stop time', 'Transaction time', 'Transaction stop time']
    #         )
    #     return DSS_Engine(db=df)

    # def retrieve_kb(self, dates):
    #     return KB(path_dec=self.path_dec, path_prod=self.path_prod)

    # def retrieve(self, dates):
    #     self.cds = self.read_db()
    #     self.kb = self.read_kb()        

    # def save_db(self):
    #     save_log = self.cds.save(db_path=self.db_path)
    #     return save_log
    


    
if __name__ == '__main__':
    st.set_page_config(page_title='CDSS', page_icon=None, layout="wide", initial_sidebar_state="auto", menu_items=None)
    ui = UI(debug_mode=False)



# with st.sidebar:
#     with st.expander("ICU Patients:"):
#         df_patients = pd.read_sql('select distinct "First name", "Last name" from patients', conn)
#         for _, row in df_patients.iterrows():
#             if self.debug_mode: st.write(row['First name'], row['Last name']) 


# df = pd.read_sql('select * from patients', conn)
# df_view = df[df.transaction_timestamp <= transaction_timestamp]
# df_view = df_view[df_view['First name'].eq('Eli') & df_view['Unit'].eq('mmHg')].set_index(['Valid start time'])
# st.line_chart(df_view[['Value']])


# st.markdown(
#     """
# <style>
#     [data-testid="column"] {
#         box-shadow: rgb(0 0 0 / 20%) 0px 2px 1px -1px, rgb(0 0 0 / 14%) 0px 1px 1px 0px, rgb(0 0 0 / 12%) 0px 1px 3px 0px;
#         border-radius: 15px;
#     } 
# </style>
# """,
#     unsafe_allow_html=True,
# )