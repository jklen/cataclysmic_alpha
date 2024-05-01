-- SQLite
select * from portfolio_state;
select * from portfolio_info;
select * from positions;

--delete from portfolio_info
--where date = '2024-04-26';

delete from portfolio_state
where portfolio_script_run_id IN ('9ebccb0d-dc60-42c1-9062-baeab3162d6a',
            '5ad39c2b-0fcf-4c88-808b-7457808db730',
            'df1300fa-34a0-44b7-a86e-f14660e54b15',
            '81a7f68d-796e-4399-8127-cd18531ae317',
            '0bb3b84b-4289-40f5-a108-4f3d063a7c6f',
            'c6c6b090-d527-4498-8a05-df8c91559d0b',
            'da44a03f-e4aa-4579-9c25-f3aaed5a7499')
            ;

delete from portfolio_info
where portfolio_script_run_id IN ('9ebccb0d-dc60-42c1-9062-baeab3162d6a',
            '5ad39c2b-0fcf-4c88-808b-7457808db730',
            'df1300fa-34a0-44b7-a86e-f14660e54b15',
            '81a7f68d-796e-4399-8127-cd18531ae317',
            '0bb3b84b-4289-40f5-a108-4f3d063a7c6f',
            'c6c6b090-d527-4498-8a05-df8c91559d0b',
            'da44a03f-e4aa-4579-9c25-f3aaed5a7499');

delete from positions
where portfolio_script_run_id IN ('9ebccb0d-dc60-42c1-9062-baeab3162d6a',
            '5ad39c2b-0fcf-4c88-808b-7457808db730',
            'df1300fa-34a0-44b7-a86e-f14660e54b15',
            '81a7f68d-796e-4399-8127-cd18531ae317',
            '0bb3b84b-4289-40f5-a108-4f3d063a7c6f',
            'c6c6b090-d527-4498-8a05-df8c91559d0b',
            'da44a03f-e4aa-4579-9c25-f3aaed5a7499');


