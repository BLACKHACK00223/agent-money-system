from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Admin, Agent, ApprovisionnementDirect, Assistant, Caisse, Transaction


class EnvoisRetraitsViewTests(TestCase):
    def setUp(self):
        admin_user = User.objects.create_user(username='admin-test', password='password')
        self.admin = Admin.objects.create(
            user=admin_user,
            nom='Admin Test',
            telephone='70000000',
            point_service='Agence Test',
        )
        Caisse.objects.filter(user=admin_user).update(
            solde_cash=Decimal('500000'),
            solde_uv=Decimal('500000'),
            solde_wave=Decimal('500000'),
        )

        agent_user = User.objects.create_user(username='agent-test', password='password')
        self.agent = Agent.objects.create(
            user=agent_user,
            nom='BLACK',
            telephone='71111111',
            created_by=self.admin,
        )
        self.client.force_login(admin_user)

    def test_filters_and_displays_operations_in_the_unified_register(self):
        operation = ApprovisionnementDirect.objects.create(
            type_operation='envoi',
            source_type='admin',
            admin_source=self.admin,
            agent_destinataire=self.agent,
            type_approvisionnement='cash',
            montant=Decimal('100000'),
            statut='entente',
        )

        response = self.client.get(
            reverse('envois_retraits'),
            {
                'q': f'ER-{operation.id:06d}',
                'statut': 'entente',
                'agent': str(self.agent.id),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['operations_count'], 1)
        self.assertContains(response, 'Registre des opérations')
        self.assertContains(response, f'ER-{operation.id:06d}')
        self.assertContains(response, 'BLACK')


class AssistantAgentViewTests(TestCase):
    def setUp(self):
        admin_user = User.objects.create_user(username='admin-test', password='password')
        self.admin = Admin.objects.create(
            user=admin_user,
            nom='Admin Test',
            telephone='70000000',
            point_service='Agence Test',
        )
        caisse_admin = admin_user.caisse
        caisse_admin.solde_cash = Decimal('500000')
        caisse_admin.solde_uv = Decimal('500000')
        caisse_admin.solde_wave = Decimal('500000')
        caisse_admin.save()

        agent_user = User.objects.create_user(username='agent-test', password='password')
        self.agent = Agent.objects.create(
            user=agent_user,
            nom='BLACK',
            telephone='71111111',
            created_by=self.admin,
        )
        caisse_agent = agent_user.caisse
        caisse_agent.solde_cash = Decimal('300000')
        caisse_agent.solde_uv = Decimal('500000')
        caisse_agent.solde_wave = Decimal('500000')
        caisse_agent.save()

        other_user = User.objects.create_user(username='agent-other', password='password')
        self.other_agent = Agent.objects.create(
            user=other_user,
            nom='WHITE',
            telephone='72222222',
            created_by=self.admin,
        )

        assistant_user = User.objects.create_user(username='assistant-agent', password='password')
        self.assistant = Assistant.objects.create(
            user=assistant_user,
            nom='Aide BLACK',
            telephone='73333333',
            admin=self.admin,
            agent=self.agent,
        )
        self.client.force_login(assistant_user)

    def test_get_caisse_renvoie_la_caisse_de_l_agent(self):
        self.assertEqual(self.assistant.get_caisse, self.agent.user.caisse)
        self.assertEqual(self.assistant.get_caisse.solde_cash, Decimal('300000'))

    def test_assistant_d_agent_voit_seulement_les_operations_de_son_agent(self):
        op_agent = ApprovisionnementDirect.objects.create(
            type_operation='envoi',
            source_type='admin',
            admin_source=self.admin,
            agent_destinataire=self.agent,
            type_approvisionnement='cash',
            montant=Decimal('100000'),
            statut='entente',
        )
        op_autre = ApprovisionnementDirect.objects.create(
            type_operation='envoi',
            source_type='admin',
            admin_source=self.admin,
            agent_destinataire=self.other_agent,
            type_approvisionnement='cash',
            montant=Decimal('200000'),
            statut='entente',
        )

        response = self.client.get(reverse('envois_retraits'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['operations_count'], 1)
        self.assertContains(response, f'ER-{op_agent.id:06d}')
        self.assertNotContains(response, f'ER-{op_autre.id:06d}')

    def test_assistant_d_agent_est_bloque_sur_son_propre_agent(self):
        response = self.client.post(
            reverse('creer_envoi_retrait'),
            {
                'type_operation': 'envoi',
                'agent_id': str(self.agent.id),
                'type_approvisionnement': 'cash',
                'montant': '50000',
                'statut': 'entente',
            },
        )

        self.client.force_login(self.admin.user)
        self.assertEqual(
            ApprovisionnementDirect.objects.filter(agent_destinataire=self.agent).count(),
            0,
        )

    def test_historique_agent_affiche_les_envois_et_retraits_du_jour(self):
        ApprovisionnementDirect.objects.create(
            type_operation='envoi',
            source_type='admin',
            admin_source=self.admin,
            agent_destinataire=self.agent,
            type_approvisionnement='uv',
            montant=Decimal('100000'),
            statut='entente',
        )
        ApprovisionnementDirect.objects.create(
            type_operation='retrait',
            source_type='admin',
            admin_source=self.admin,
            agent_destinataire=self.agent,
            type_approvisionnement='wave',
            montant=Decimal('40000'),
            statut='valide',
        )

        self.client.force_login(self.agent.user)
        response = self.client.get(reverse('historique_agent'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['transactions']), 2)
        self.assertContains(response, '↓ Envoi UV Touchpoint')
        self.assertContains(response, '↑ Retrait UV Wave')
        self.assertContains(response, 'ER-')
        self.assertContains(response, '✓ Valide')
        self.assertEqual(response.context['total_entree'], Decimal('100000'))
        self.assertEqual(response.context['total_sortie'], Decimal('40000'))

    def test_depot_assistant_d_agent_credite_la_caisse_de_l_agent(self):
        self.assertEqual(self.assistant.get_caisse.solde_cash, Decimal('300000'))
        self.assertEqual(self.admin.user.caisse.solde_cash, Decimal('500000'))

        Transaction.objects.create(
            user=self.assistant.user,
            role='assistant',
            assistant_admin=self.admin,
            operateur='orange',
            type_transaction='depot',
            numero_client='83669820',
            montant=Decimal('2000'),
        )

        agent_caisse = Caisse.objects.get(user=self.agent.user)
        admin_caisse = Caisse.objects.get(user=self.admin.user)
        self.assertEqual(agent_caisse.solde_cash, Decimal('302000'))
        self.assertEqual(agent_caisse.solde_uv, Decimal('498000'))
        self.assertEqual(admin_caisse.solde_cash, Decimal('500000'))
        self.assertEqual(admin_caisse.solde_uv, Decimal('500000'))

    def test_historique_agent_affiche_montant_et_reference_des_transactions(self):
        tx = Transaction.objects.create(
            user=self.agent.user,
            role='agent',
            operateur='orange',
            type_transaction='credit',
            numero_client='83669820',
            montant=Decimal('3000'),
        )

        self.client.force_login(self.agent.user)
        response = self.client.get(reverse('historique_agent'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '● Crédit Orange Money')
        self.assertContains(response, '3\u00a0000 F')
        self.assertContains(response, tx.reference)
        self.assertContains(response, '83 66 98 20')

    def test_historique_agent_affiche_les_transactions_de_ses_assistants(self):
        tx_assistant = Transaction.objects.create(
            user=self.assistant.user,
            role='assistant',
            assistant_admin=self.admin,
            operateur='orange',
            type_transaction='depot',
            numero_client='83669820',
            montant=Decimal('2000'),
        )
        tx_agent = Transaction.objects.create(
            user=self.agent.user,
            role='agent',
            operateur='orange',
            type_transaction='depot',
            numero_client='80000000',
            montant=Decimal('5000'),
        )

        self.client.force_login(self.agent.user)
        response = self.client.get(reverse('historique_agent'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['transactions']), 2)
        self.assertContains(response, tx_assistant.reference)
        self.assertContains(response, tx_agent.reference)
        self.assertContains(response, 'Aide BLACK (Assistant)')
        self.assertContains(response, 'BLACK (Agent)')


class SecuriteTransactionsTests(TestCase):
    """Protections ajoutées : autorisation d'annulation et cohérence des soldes."""

    def setUp(self):
        admin_user = User.objects.create_user(username='admin-test', password='password')
        self.admin = Admin.objects.create(
            user=admin_user,
            nom='Admin Test',
            telephone='70000000',
            point_service='Agence Test',
        )
        Caisse.objects.filter(user=admin_user).update(
            solde_cash=Decimal('500000'),
            solde_uv=Decimal('500000'),
            solde_wave=Decimal('500000'),
        )

        agent_user = User.objects.create_user(username='agent-test', password='password')
        self.agent = Agent.objects.create(
            user=agent_user,
            nom='BLACK',
            telephone='71111111',
            created_by=self.admin,
        )
        Caisse.objects.filter(user=agent_user).update(
            solde_cash=Decimal('300000'),
            solde_uv=Decimal('200000'),
            solde_wave=Decimal('200000'),
        )

        other_user = User.objects.create_user(username='agent-other', password='password')
        self.other_agent = Agent.objects.create(
            user=other_user,
            nom='WHITE',
            telephone='72222222',
            created_by=self.admin,
        )

    def _creer_transaction(self):
        return Transaction.objects.create(
            user=self.agent.user,
            role='agent',
            operateur='orange',
            type_transaction='depot',
            numero_client='83669820',
            montant=Decimal('2000'),
        )

    def test_annulation_par_un_autre_agent_non_admin_est_refusee(self):
        tx = self._creer_transaction()
        self.client.force_login(self.other_agent.user)

        response = self.client.post(
            reverse('api_annuler_transaction'),
            {'reference': tx.reference, 'motif': 'test'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['success'])
        self.assertIn('pas autorisé', response.json()['error'])
        tx.refresh_from_db()
        self.assertFalse(tx.est_annule)
        self.assertEqual(tx.date_annulation, None)

    def test_annulation_par_l_auteur_reussit_et_inverse_les_soldes(self):
        tx = self._creer_transaction()
        self.client.force_login(self.agent.user)

        response = self.client.post(
            reverse('api_annuler_transaction'),
            {'reference': tx.reference, 'motif': 'erreur de saisie'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        tx.refresh_from_db()
        self.assertTrue(tx.est_annule)
        self.assertEqual(tx.motif_annulation, 'erreur de saisie')
        caisse = Caisse.objects.get(user=self.agent.user)
        self.assertEqual(caisse.solde_cash, Decimal('300000'))
        self.assertEqual(caisse.solde_uv, Decimal('200000'))

    def test_annulation_par_admin_reussit(self):
        tx = self._creer_transaction()
        self.client.force_login(self.admin.user)

        response = self.client.post(
            reverse('api_annuler_transaction'),
            {'reference': tx.reference, 'motif': 'test admin'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        tx.refresh_from_db()
        self.assertTrue(tx.est_annule)

    def test_double_annulation_est_refusee(self):
        tx = self._creer_transaction()
        self.client.force_login(self.admin.user)
        first = self.client.post(
            reverse('api_annuler_transaction'),
            {'reference': tx.reference, 'motif': 'test'},
        )
        second = self.client.post(
            reverse('api_annuler_transaction'),
            {'reference': tx.reference, 'motif': 'test'},
        )

        self.assertTrue(first.json()['success'])
        self.assertFalse(second.json()['success'])
        self.assertIn('déjà annulée', second.json()['error'])
        tx.refresh_from_db()
        self.assertTrue(tx.est_annule)

    def test_envoi_depassant_le_solde_est_refuse_sans_toucher_les_caisses(self):
        self.client.force_login(self.admin.user)
        solde_cash_avant = Caisse.objects.get(user=self.admin.user).solde_cash

        response = self.client.post(
            reverse('creer_envoi_retrait'),
            {
                'type_operation': 'envoi',
                'agent_id': str(self.agent.id),
                'type_approvisionnement': 'cash',
                'montant': '600000',
                'statut': 'valide',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['success'])
        self.assertIn('Solde Argent insuffisant', response.json()['error'])
        self.assertEqual(ApprovisionnementDirect.objects.count(), 0)
        self.assertEqual(Caisse.objects.get(user=self.admin.user).solde_cash, solde_cash_avant)

    def test_retrait_depassant_le_solde_uv_de_l_agent_est_refuse(self):
        self.client.force_login(self.admin.user)
        solde_uv_agent = Caisse.objects.get(user=self.agent.user).solde_uv

        response = self.client.post(
            reverse('creer_envoi_retrait'),
            {
                'type_operation': 'retrait',
                'agent_id': str(self.agent.id),
                'type_approvisionnement': 'uv',
                'montant': '300000',
                'statut': 'valide',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['success'])
        self.assertIn('UV Touchpoint de l\'agent insuffisant', response.json()['error'])
        self.assertEqual(Caisse.objects.get(user=self.agent.user).solde_uv, solde_uv_agent)
