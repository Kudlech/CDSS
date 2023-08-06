
import pandas as pd
import io
import numpy as np
import datetime
import streamlit as st
from dss_engine import DSS_Engine
from KnowledgeBase import KB


class UI():
    def __init__(self, db_path='project_db_updated.csv', debug_mode=False) -> None:
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

        # [UI] title
        # st.title('Decision Support Systems in Medicine - Mini Project', anchor=False)

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
        st.sidebar.title('Decision Support Systems in Medicine - Mini Project')
        demo_name = st.sidebar.radio("Choose a page", self.page_names_to_funcs.keys())
        self.page_names_to_funcs[demo_name]()

    def page_home(self):
        _df = self.cds.db.copy()
        _df['Full name'] = _df['First name'] + ' ' + _df['Last name']
        patient_full_name_list = list(_df.drop_duplicates(['ID', 'First name', 'Last name'])['Full name'])

        no_patient_selected_placeholder_str = '---'
        col_patient_selction, col_state_display, _, _ = st.columns(4)

        with col_patient_selction:        
            selected_patient = st.selectbox(f'Select patient name:', [no_patient_selected_placeholder_str] + patient_full_name_list)

        
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
    

            df_states = patient_data[~patient_data['LOINC-NUM'].eq('Gender')].drop_duplicates('ID')[['ID', 'First name', 'Last name'] + list(set(df_db_inf['State type']))]
            st.write('🌡️ Patient states:')
            with col_state_display:
                st.metric('**Total number of patients:**', len(set(df_states['ID'])))

            # state_names = list(set(df_db_inf['State type']))
            # state_names.sort()
            # max_number_of_unique_state_values = 1
            # for state_type in state_names:
            #     number_of_state_values = len(set(df_states[state_type].value_counts().keys()))
            #     max_number_of_unique_state_values = max(max_number_of_unique_state_values, number_of_state_values)

            # for state_type in state_names:
            #     df_state_value_counts = df_states[state_type].value_counts()
            #     df_state_value_counts_keys = list(set(df_state_value_counts.keys()))
            #     df_state_value_counts_keys.sort()
            #     cols_ = st.columns(max_number_of_unique_state_values)
            #     for k_col, k in zip(cols_, df_state_value_counts_keys):      
            #         with k_col:
            #             st.metric(f'**{state_type}**  \n  *{k}*', df_state_value_counts[k])
            
            st.dataframe(df_states, hide_index=True)
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
            patient_data = patient_data.copy()
            patient_data.insert(4,'LOINC-NAME', patient_data['LOINC-NUM'].map(dict(self.cds.kb.kb_dec.get_full_loinc_desc().values)))
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
            loinc_num_full_list = list(set(list(_df.drop_duplicates(['LOINC-NUM'])['LOINC-NUM'])) - set(['Gender']))
            loinc_num_full_list = [f'{loinc_num} -- {dict(self.cds.kb.kb_dec.get_full_loinc_desc().values)[loinc_num]}' for loinc_num in loinc_num_full_list]
            selected_loinc = st.selectbox('LOINC-NUM:  ', loinc_num_full_list)
            selected_loinc = selected_loinc.split(' -- ')[0]
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
                day=  self.cds.db[~(self.cds.db['LOINC-NUM'] == 'Gender')]['Valid start time'].min().day, 
                month=self.cds.db[~(self.cds.db['LOINC-NUM'] == 'Gender')]['Valid start time'].min().month, 
                year= self.cds.db[~(self.cds.db['LOINC-NUM'] == 'Gender')]['Valid start time'].min().year
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
            time_from_valid = st.time_input('From valid time', datetime.time(hour=self.cds.db[~(self.cds.db['LOINC-NUM'] == 'Gender')]['Valid start time'].min().hour, 
                                                                             minute=self.cds.db[~(self.cds.db['LOINC-NUM'] == 'Gender')]['Valid start time'].min().minute), 
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

        selected_current_date = f'{self.date_current}'
        selected_current_time = f'{self.time_current.hour}:{self.time_current.minute}'
        selected_from_valid_date = f'{date_from_valid}'
        selected_from_valid_time = '.' if time_from_valid_value == None else f'{time_from_valid_value.hour}:{time_from_valid_value.minute}'
        selected_to_valid_date = f'{date_to_valid}'
        selected_to_valid_time = '.' if time_to_valid_value == None else f'{time_to_valid_value.hour}:{time_to_valid_value.minute}'
        history_retrieve_command_preview_text = f'History of the LOINC-NUM **{selected_loinc}** values of the patient **{selected_patient}** at the time **{selected_current_date}** **{selected_current_time}** that were taken from time **{selected_from_valid_date}** **{selected_from_valid_time}** to time **{selected_to_valid_date}** **{selected_to_valid_time}**'
        st.info(history_retrieve_command_preview_text, icon="🗒️")

        patient_histroy_data = patient_histroy_data.copy()
        patient_histroy_data.insert(4,'LOINC-NAME', patient_histroy_data['LOINC-NUM'].map(dict(self.cds.kb.kb_dec.get_full_loinc_desc().values)))
        st.dataframe(patient_histroy_data, hide_index=True)

    def page_update(self):
        col_inputs_left, col_new_loinc_value, _ = st.columns([2,1, 1])

        with col_inputs_left:
            col_patient_selection, col_loinc_selection = st.columns(2)
            col_valid_date_picker, col_valid_time_picker = st.columns(2)
            
            with col_loinc_selection:
                _df = self.cds.db.copy()
                loinc_num_full_list = list(set(list(_df.drop_duplicates(['LOINC-NUM'])['LOINC-NUM'])) - set(['Gender']))
                loinc_num_full_list = [f'{loinc_num} -- {dict(self.cds.kb.kb_dec.get_full_loinc_desc().values)[loinc_num]}' for loinc_num in loinc_num_full_list]
                selected_loinc = st.selectbox('LOINC-NUM:', loinc_num_full_list)
                selected_loinc = selected_loinc.split(' -- ')[0]
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

        selected_current_date = f'{self.date_current}'
        selected_current_time = f'{self.time_current.hour}:{self.time_current.minute}'
        selected_valid_date = f'{date_valid}'
        selected_valid_time = None if time_valid_value == None else f'{time_valid_value.hour}:{time_valid_value.minute}'
        update_command_preview_text = f'Update at **{selected_current_date} {selected_current_time}** LOINC-NUM **{selected_loinc}** with **a new value** for patient **{selected_patient}** at valid time **{selected_valid_date} {"." if selected_valid_time == None else selected_valid_time}**'
        st.info(update_command_preview_text, icon="🖊️")

        selected_row_preview, _ = self.cds.update(
            loinc=selected_loinc, 
            first_name=selected_patient.split()[0], 
            last_name=selected_patient.split()[1], 
            trans_date=f'{self.date_current}', 
            trans_time=f'{self.time_current.hour}:{self.time_current.minute}', 
            component_date=f'{date_valid}', 
            component_time=None if time_valid_value == None else f'{time_valid_value.hour}:{time_valid_value.minute}',
            new_value=text_input_new_loinc_value,
            only_preview_selected_row = True
            )    
        if type(selected_row_preview) == int and selected_row_preview == -1:
            st.warning('Data not selected')              

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
                st.success('Data update', icon="🖊️")
                self.cds.save(self.db_path)
                st.write('Selected row:')
                st.write(selected_row, hide_index=True)
                st.write('New row:')
                st.write(new_row, hide_index=True)

        max_valid_datetime = self.cds.db['Valid start time'].max()
        max_valid_date = datetime.date(day=  max_valid_datetime.day,  month=  max_valid_datetime.month, year= max_valid_datetime.year)
        max_valid_time = datetime.time(hour= max_valid_datetime.hour, minute= max_valid_datetime.minute)

        min_valid_datetime = self.cds.db[~(self.cds.db['LOINC-NUM'] == 'Gender')]['Valid start time'].min()
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
        to_time=None #f'{max_valid_time.hour}:{max_valid_time.minute}',
        )
        st.write('Retrieved history:')
        patient_histroy_data = patient_histroy_data.copy()
        patient_histroy_data.insert(4,'LOINC-NAME', patient_histroy_data['LOINC-NUM'].map(dict(self.cds.kb.kb_dec.get_full_loinc_desc().values)))

        try:
            st.dataframe(patient_histroy_data.style.apply(lambda x: ['background-color: lemonchiffon' if x.name in list(selected_row_preview.index) else '' for i in x], axis=1), hide_index=True)
        except:
            st.dataframe(patient_histroy_data, hide_index=True)
        

    def page_delete(self):
        col_patient_selection, col_loinc_selection,  col_use_current_time, _= st.columns(4)
        col_valid_date_picker, col_valid_time_picker, col_deletion_date_picker, col_deletion_time_picker = st.columns(4)  
        col_delete, _,  _, _= st.columns(4)
        
        with col_loinc_selection:
            _df = self.cds.db.copy()
            loinc_num_full_list = list(set(list(_df.drop_duplicates(['LOINC-NUM'])['LOINC-NUM'])) - set(['Gender']))
            loinc_num_full_list = [f'{loinc_num} -- {dict(self.cds.kb.kb_dec.get_full_loinc_desc().values)[loinc_num]}' for loinc_num in loinc_num_full_list]
            selected_loinc = st.selectbox('LOINC-NUM: ', loinc_num_full_list)
            selected_loinc = selected_loinc.split(' -- ')[0]
            if self.debug_mode: st.write(selected_loinc)
                    
        with col_patient_selection:
            _df = self.cds.db.copy()
            _df['Full name'] = _df['First name'] + ' ' + _df['Last name']
            patient_full_name_list = list(_df.drop_duplicates(['ID', 'First name', 'Last name'])['Full name'])
            selected_patient = st.selectbox('Patient name:', patient_full_name_list)
            if self.debug_mode: st.write(selected_patient)

        with col_use_current_time:
            st.write('')
            st.write('')
            checkbox_use_current_time = st.checkbox('Use current time', value=False)

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

        with col_deletion_date_picker:
            date_deletion = st.date_input(
                "Deletion date: ",
                (datetime.date(
                day=self.cds.db['Valid start time'].max().day, 
                month=self.cds.db['Valid start time'].max().month, 
                year=self.cds.db['Valid start time'].max().year
                )), format='DD/MM/YYYY', disabled=(not checkbox_use_current_time)
            ) 
            if self.debug_mode: st.write(date_deletion)


        with col_valid_time_picker:
            time_valid = st.time_input('Valid time:', datetime.time(hour=self.cds.db['Valid start time'].max().hour, minute=self.cds.db['Valid start time'].max().minute), 
                                       step=600,
                                    #    disabled=(not button_valid_time_disabler),
                                       )
            time_valid_value = time_valid# if button_valid_time_disabler else None
            if self.debug_mode: st.write(time_valid_value)

        with col_deletion_time_picker:
            time_deletion = st.time_input('Deletion time:', datetime.time(hour=self.cds.db['Valid start time'].max().hour, minute=self.cds.db['Valid start time'].max().minute), 
                                       step=600,
                                       disabled=(not checkbox_use_current_time),
                                       )
            if self.debug_mode: st.write(time_deletion)

        


        selected_deletion_date = f'{self.date_current}' if not checkbox_use_current_time else f'{date_deletion}'
        selected_deletion_time = f'{self.time_current.hour}:{self.time_current.minute}' if not checkbox_use_current_time else f'{time_deletion.hour}:{time_deletion.minute}'
        selected_valid_date = f'{date_valid}'
        selected_valid_time = None if time_valid_value == None else f'{time_valid_value.hour}:{time_valid_value.minute}'
        delete_command_preview_text = f'Delete at **{selected_deletion_date} {selected_deletion_time}** LOINC-NUM **{selected_loinc}** of patient **{selected_patient}** that was taken at time **{selected_valid_date} {"." if selected_valid_time == None else selected_valid_time}**'
        st.info(delete_command_preview_text, icon="❌")
        

        selected_row_preview = self.cds.delete(
                        loinc=selected_loinc, 
                        first_name=selected_patient.split()[0], 
                        last_name=selected_patient.split()[1], 
                        trans_date=selected_deletion_date, 
                        trans_time= selected_deletion_time, 
                        component_date=selected_valid_date, 
                        component_time=selected_valid_time,
                        only_preview_selected_row=True
                        )

        # with col_delete:       
        if type(selected_row_preview) == int and selected_row_preview == -1:
            st.warning('Data not selected')
        button_delete = st.button('Submit')
        
        if button_delete:
            selected_row = self.cds.delete(
                        loinc=selected_loinc, 
                        first_name=selected_patient.split()[0], 
                        last_name=selected_patient.split()[1], 
                        trans_date=selected_deletion_date, 
                        trans_time= selected_deletion_time, 
                        component_date=selected_valid_date, 
                        component_time=selected_valid_time
                        )
            if type(selected_row) == int and selected_row == -1: 
                st.error('Data does not exist', icon="🚨")
            else:
                self.cds.save(self.db_path)
                st.write('Deleted row:')
                st.dataframe(selected_row, hide_index=True)
                st.success('Deleted data successfully', icon="❌")
                
        

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
        to_time=None#f'{max_valid_time.hour}:{max_valid_time.minute}',
        )

        
        patient_histroy_data = patient_histroy_data.copy()
        patient_histroy_data.insert(4,'LOINC-NAME', patient_histroy_data['LOINC-NUM'].map(dict(self.cds.kb.kb_dec.get_full_loinc_desc().values)))
        
        st.write('Retrieved history:')
        try:
            st.dataframe(patient_histroy_data.style.apply(lambda x: ['background-color: lightcoral' if x.name in [list(selected_row_preview.index)[0]] else '' for i in x], axis=1), hide_index=False)
        except Exception as e:
            st.dataframe(patient_histroy_data, hide_index=False)


          
    def page_retrieve(self):
        col_patient_selection, col_loinc_selection, _, _ = st.columns(4)
        col_valid_date_picker, col_valid_time_picker, col_valid_time_disabler, _ = st.columns(4)  

        with col_loinc_selection:
            _df = self.cds.db.copy()
            loinc_num_full_list = list(set(list(_df.drop_duplicates(['LOINC-NUM'])['LOINC-NUM'])) - set(['Gender']))
            loinc_num_full_list = [f'{loinc_num} -- {dict(self.cds.kb.kb_dec.get_full_loinc_desc().values)[loinc_num]}' for loinc_num in loinc_num_full_list]
            selected_loinc = st.selectbox('LOINC-NUM:   ', loinc_num_full_list)
            selected_loinc = selected_loinc.split(' -- ')[0]
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
        
        selected_current_date = f'{self.date_current}'
        selected_current_time = f'{self.time_current.hour}:{self.time_current.minute}'
        selected_valid_date = f'{date_valid}'
        selected_valid_time = '.' if time_valid_value == None else f'{time_valid_value.hour}:{time_valid_value.minute}'
        retrieve_command_preview_text = f'Retrieve the LOINC-NUM **{selected_loinc}** value of the patient **{selected_patient}** at the time **{selected_current_date}** **{selected_current_time}** that was taken at time **{selected_valid_date}** **{selected_valid_time}**'
        st.info(retrieve_command_preview_text, icon="⬇️")
        
        st.write('Retrieved data:')
        st.dataframe(patient_data, hide_index=False)



    
if __name__ == '__main__':
    st.set_page_config(page_title='CDSS', page_icon=None, layout="wide", initial_sidebar_state="auto", menu_items=None)
    ui = UI(debug_mode=False)