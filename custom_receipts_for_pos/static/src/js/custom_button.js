/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PartnerDetailsEdit } from "@point_of_sale/app/screens/partner_list/partner_editor/partner_editor";
import { ErrorPopup } from "@point_of_sale/app/errors/popups/error_popup";
import { _t } from "@web/core/l10n/translation";

import { useService } from "@web/core/utils/hooks";
patch(PartnerDetailsEdit.prototype, {
  setup() {
    this.rpc = useService("rpc");
    super.setup(...arguments);
    this.changes.street = "Ciudad";
    Object.assign(this.props.imperativeHandle, {
      processNitVerification: () => this.processNitVerification(),
    });
  },

  async processNitVerification() {
    try {
      const vat = this.changes.vat;

      if (!vat) {
        return this.popup.add(ErrorPopup, {
          title: _t("Error"),
          body: _t("El campo NIT está vacío.\nPor favor, ingrese un NIT válido."),
        });
      }

      // ======= AQUÍ EL ÚNICO CAMBIO: llamar al controlador =======
      // En vez de fetch() directo al FEEL, usamos rpc() al backend
  
      const data = await this.rpc("/pos/nuc_lookup", { vat });
      // ===========================================================
      console.log(data)
      console.log(data.ok)
      if (data.ok) {
        let nameParts = data.data.name;
  
        this.changes.name = nameParts;
        this.changes.city = data.data.city
        if (data.data.country_id) this.changes.country_id = data.data.country_id;
        if (data.data.state_id)   this.changes.state_id   = data.data.state_id;
      } else {
        return this.popup.add(ErrorPopup, {
          title: _t("Error"),
          body: _t(data.error),
        });
      }

    } catch (error) {
      console.error("Error during fetch:", error);
      return this.popup.add(ErrorPopup, {
        title: _t("Error durante la consulta"),
        body: _t("Error al consultar el NIT.\nPor favor, intente nuevamente o consulte al desarrollador."),
      });
    }
  },
});
