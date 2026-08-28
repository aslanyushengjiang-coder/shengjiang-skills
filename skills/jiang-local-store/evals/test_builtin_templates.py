"""Local regression for bundled deterministic SVG templates (stdlib only)."""
from pathlib import Path
import base64
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('fill_builtin_template',ROOT/'scripts/fill_builtin_template.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
PHOTO=ROOT/'assets/demo/dish-photo.png'
BACKGROUND=ROOT/'assets/demo/campaign-background.png'
STYLE_REF=ROOT/'assets/style-references/tomato-beef-brand-reference.png'


class BuiltinTemplateTest(unittest.TestCase):
    def setUp(self):
        parent=Path(os.environ.get('LOCAL_STORE_TEMPLATE_TEST_DIR',tempfile.gettempdir()))
        parent.mkdir(parents=True,exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(prefix='builtin-',dir=parent)
        self.work=Path(self.tmp.name)

    def tearDown(self): self.tmp.cleanup()

    def sample(self,template):
        data={'facts_source':'isolated fixture only','source_role':'demo-fixture','truth_status':'fictional_demo',
              'truth_disclosure':'虚构演示案例 · AI图片 · 不可投放','store_name':'姜小面测试店',
              'dish_image':str(PHOTO),'brand_ink':'#7A2F2A'}
        if template=='top-space-poster':
            data.update({'background_image':str(BACKGROUND),'headline_1':'番茄牛腩面',
                         'headline_2':'开业活动说明','offer_line':'原价￥28.00 · 活动价￥25.00',
                         'rule_1':'无需预约；不与其他优惠同享'})
        elif template=='dish-photo-card':
            data.update({'item_id':'demo-dish-001','dish_name':'番茄牛腩面','spec_line':'单人份｜不辣',
                         'price_line':'菜单价￥28.00','paper_color':'#F5EEE4','photo_well_color':'#E8C8A2'})
        else:
            data.update({'headline':'开业测试活动','date':'2026年10月1日—10月7日',
                         'price_line':'￥25.00','background_color':'#F5EEE4','decoration_color':'#D9684D','footer_color':'#A44835'})
        return data

    def render(self,template,data=None):
        data=data if data is not None else self.sample(template)
        source=self.work/(template+'.json')
        source.write_text(json.dumps(data,ensure_ascii=False))
        output=self.work/(template+'.svg')
        result=module.render(template,source,output)
        return output,result

    def test_three_templates_embed_original_image_and_keep_copy(self):
        expected=hashlib.sha256(PHOTO.read_bytes()).hexdigest()
        for name in module.CONFIG:
            with self.subTest(name=name):
                output,result=self.render(name)
                svg=output.read_text();root=ET.fromstring(svg)
                self.assertNotIn('{{',svg)
                self.assertFalse(result['raster_exported'])
                self.assertFalse(result['visual_checked'])
                self.assertFalse(result['published'])
                image_nodes=root.findall('.//{http://www.w3.org/2000/svg}image')
                decoded=[]
                for image in image_nodes:
                    href=image.get('href');self.assertTrue(href.startswith('data:image/png;base64,'))
                    decoded.append(hashlib.sha256(base64.b64decode(href.split(',',1)[1],validate=True)).hexdigest())
                self.assertIn(expected,decoded)
                self.assertIn('虚构演示案例',''.join(root.itertext()))
                if name=='dish-photo-card':
                    self.assertEqual(root.find(".//*[@id='exact-price']").text,'菜单价￥28.00')

    def test_svg_is_portable_after_move(self):
        output,_=self.render('dish-photo-card')
        moved=self.work/'moved-away/only-file.svg';moved.parent.mkdir();shutil.copyfile(output,moved)
        root=ET.fromstring(moved.read_text())
        for node in root.iter():
            if 'href' in node.attrib:
                raw=base64.b64decode(node.get('href').split(',',1)[1],validate=True)
                self.assertEqual(raw,PHOTO.read_bytes())

    def test_xml_sensitive_copy_is_preserved_as_text(self):
        data=self.sample('dish-photo-card');data['dish_name']='鱼 & "汤" <鲜>'
        output,_=self.render('dish-photo-card',data)
        root=ET.fromstring(output.read_text())
        self.assertEqual(root.find(".//*[@id='exact-dish-name']").text,data['dish_name'])
        self.assertFalse(root.findall('.//script'))

    def test_unknown_required_fact_is_blocked_without_output(self):
        data=self.sample('dish-photo-card');data['dish_name']='unknown'
        with self.assertRaisesRegex(ValueError,'blocked-missing-fact'):
            self.render('dish-photo-card',data)
        self.assertFalse((self.work/'dish-photo-card.svg').exists())

    def test_missing_photo_is_blocked(self):
        data=self.sample('dish-photo-card');data['dish_image']='missing.png'
        with self.assertRaisesRegex(ValueError,'blocked-missing-input'):
            self.render('dish-photo-card',data)

    def test_style_reference_is_not_a_sku_photo(self):
        data=self.sample('dish-photo-card');data['dish_image']=str(STYLE_REF)
        with self.assertRaisesRegex(ValueError,'style-reference-only'):
            self.render('dish-photo-card',data)

    def test_source_roles_cannot_upgrade_demo_or_style(self):
        data=self.sample('dish-photo-card');data['source_role']='style-only'
        with self.assertRaisesRegex(ValueError,'source_role'):
            self.render('dish-photo-card',data)
        data=self.sample('dish-photo-card');data['truth_status']='real_store_confirmed'
        with self.assertRaisesRegex(ValueError,'cannot be upgraded'):
            self.render('dish-photo-card',data)

    def test_long_copy_is_not_silently_truncated(self):
        data=self.sample('top-space-poster');data['headline_1']='标题'*20
        with self.assertRaisesRegex(ValueError,'length budget'):
            self.render('top-space-poster',data)

    def test_fictional_demo_requires_visible_disclosure(self):
        data=self.sample('dish-photo-card');data['truth_disclosure']='成品海报'
        with self.assertRaisesRegex(ValueError,'Fictional examples'):
            self.render('dish-photo-card',data)

    def test_festival_revision_preserves_protected_layers(self):
        source,_=self.render('festival-locked')
        changes=self.work/'changes.json';changes.write_text(json.dumps({'date':'2027年2月6日—2月12日','background_color':'#F8E7D0','decoration_color':'#C83D2F','footer_color':'#B32622'},ensure_ascii=False))
        target=self.work/'revised.svg'
        result=module.revise_festival(source,changes,target)
        self.assertTrue(all(x['identical'] for x in result['protected_layers']))
        self.assertEqual(len(result['protected_layers']),5)
        self.assertEqual(ET.fromstring(target.read_text()).find(".//*[@id='change-date']").text,'2027年2月6日—2月12日')
        self.assertEqual(set(result['changed_layers']),{'change-date','change-background-base','change-background-decoration-1','change-background-decoration-2'})
        self.assertEqual(ET.fromstring(source.read_text()).find(".//*[@id='protected-price']")[0].text,'￥25.00')
        before_bg=ET.fromstring(source.read_text()).find(".//*[@id='disclosure-background']")
        after_bg=ET.fromstring(target.read_text()).find(".//*[@id='disclosure-background']")
        self.assertIsNotNone(before_bg)
        self.assertEqual(before_bg.get('fill'),'#F5EEE4')
        self.assertEqual(ET.tostring(before_bg),ET.tostring(after_bg))

    def test_festival_rejects_price_change(self):
        source,_=self.render('festival-locked')
        changes=self.work/'changes.json';changes.write_text('{"price_line":"￥19.90"}')
        with self.assertRaisesRegex(ValueError,'Change Set'):
            module.revise_festival(source,changes,self.work/'invalid.svg')

    def test_missing_logo_or_qr_does_not_create_fake_assets(self):
        output,manifest=self.render('festival-locked')
        root=ET.fromstring(output.read_text())
        self.assertEqual(len(root.find(".//*[@id='protected-qr']")),0)
        self.assertEqual(manifest['qr_status'],'not-provided; no fake QR created')
        self.assertIn('not a logo',manifest['logo_status'])


if __name__=='__main__': unittest.main(verbosity=2)
