def migrate(cr, version):
    cr.execute('''
ALTER TABLE gift_card DROP CONSTRAINT IF EXISTS gift_card_unique_gift_card_code;
    ''')
