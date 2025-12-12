{
    'name': 'NUC FACTURACION GUATEMALA', 
    'summary': 'Modulo Conexion Facturacion FEL NUC',
    'description': '''
       Conexion Facturacion FEL GUATEMALA.
    ''',
    'version': '17.0.0.0.0',
    'license': 'LGPL-3', 
    'author': 'Jonatan Garcia Dev -> Garciajonatan56@gmail.com',
 

    'depends': [
        'base','l10n_gt', 'account'

      
    ],
 
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
     
        'views/res_company.xml',
        'views/view.xml',
        'views/account_move.xml',
        'views/account_move_annul.xml',
        'views/res_partner.xml',
        'reports/account_move_report.xml'
    ],
   
   
    'installable': True,
    'application': True,
    'auto_install': False,

}
