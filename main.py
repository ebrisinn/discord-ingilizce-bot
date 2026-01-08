import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import aiohttp
from datetime import datetime, timedelta

# Bot ayarları
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

# Kelime listeleri
KELIMELER = {
    "kolay": [
        "cat", "dog", "house", "book", "water", "food", "friend", "happy",
        "run", "sleep", "beautiful", "small", "big", "love", "family",
        "school", "teacher", "student", "phone", "computer", "game", "music"
    ],
    "orta": [
        "adventure", "curious", "delicious", "energetic", "fantastic",
        "generous", "imagine", "journey", "knowledge", "magnificent",
        "necessary", "opportunity", "particular", "question", "remember",
        "situation", "temperature", "understand", "vacation", "wonderful"
    ],
    "zor": [
        "philosophical", "extraordinary", "consciousness", "metaphorical",
        "simultaneously", "revolutionary", "sophisticated", "psychological",
        "archaeological", "characteristic", "environmental", "entrepreneurial",
        "unprecedented", "abbreviation", "conscientious", "infrastructure"
    ]
}

# Oyun verileri
aktif_oyunlar = {}

# Motivasyon mesajları
MOTIVASYON = [
    "🧠 Beynini bilim adamları incelemeli!",
    "🚀 NASA seni çağırıyor!",
    "👑 Shakespeare bile kıskandı!",
    "🎯 Oxford sözlüğüne geçtin!",
    "⚡ Einstein: 'Bu çocuk dâhi!'",
    "🌟 Grammy ödülü kazandın!",
    "🔥 Cambridge kapıları açık!",
    "💎 Bu cümleyi müzeye koymalıyız!",
    "🦄 Unicorn bile bu kadar nadir!",
    "🎪 Cirque du Soleil bile bu kadar akrobasi yapamaz!"
]

# Grammar kontrolü
async def grammar_kontrol(cumle):
    """LanguageTool API ile grammar kontrolü"""
    try:
        url = "https://api.languagetool.org/v2/check"
        data = {
            "text": cumle,
            "language": "en-US"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    result = await response.json()
                    hatalar = result.get("matches", [])
                    
                    # Önemli hataları filtrele
                    onemli_hatalar = [
                        h for h in hatalar
                        if h.get("rule", {}).get("issueType") in ["grammar", "misspelling"]
                    ]
                    
                    return {
                        "hatali": len(onemli_hatalar) > 0,
                        "hatalar": onemli_hatalar[:3]
                    }
    except Exception as e:
        print(f"Grammar kontrol hatası: {e}")
    
    return {"hatali": False, "hatalar": []}

# Puan hesaplama
def puan_hesapla(cumle, kelime):
    """Kelime sayısına göre puan hesapla"""
    kelime_sayisi = len(cumle.split())
    
    if kelime.lower() not in cumle.lower():
        return 0
    
    # Her kelime = 1 puan
    puan = kelime_sayisi
    
    # Bonuslar
    if kelime_sayisi >= 10:
        puan += 5
    if kelime_sayisi >= 15:
        puan += 5
    if "," in cumle:
        puan += 1
    
    return puan

@bot.event
async def on_ready():
    print(f"✅ {bot.user} olarak giriş yapıldı!")
    print(f"✅ Bot {len(bot.guilds)} sunucuda aktif!")
    
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} komut senkronize edildi!")
    except Exception as e:
        print(f"❌ Hata: {e}")

@bot.tree.command(name="yaris-basla", description="İngilizce yarışı başlat!")
@app_commands.describe(
    seviye="Kelime zorluğu",
    sure="Yarış süresi (dakika)",
    kisi_sayisi="Katılımcı sayısı (2-10)"
)
@app_commands.choices(seviye=[
    app_commands.Choice(name="Kolay", value="kolay"),
    app_commands.Choice(name="Orta", value="orta"),
    app_commands.Choice(name="Zor", value="zor")
])
@app_commands.choices(sure=[
    app_commands.Choice(name="1 Dakika", value=1),
    app_commands.Choice(name="3 Dakika", value=3),
    app_commands.Choice(name="5 Dakika", value=5)
])
async def yaris_basla(
    interaction: discord.Interaction,
    seviye: app_commands.Choice[str],
    sure: app_commands.Choice[int],
    kisi_sayisi: int = 5
):
    kanal_id = interaction.channel_id
    
    # Aktif oyun kontrolü
    if kanal_id in aktif_oyunlar:
        await interaction.response.send_message(
            "❌ Bu kanalda zaten oyun var!",
            ephemeral=True
        )
        return
    
    if kisi_sayisi < 2 or kisi_sayisi > 10:
        await interaction.response.send_message(
            "⚠️ Kişi sayısı 2-10 arası olmalı!",
            ephemeral=True
        )
        return
    
    # Oyun verilerini başlat
    seviye_str = seviye.value
    sure_int = sure.value
    
    aktif_oyunlar[kanal_id] = {
        "seviye": seviye_str,
        "sure": sure_int,
        "kisi_sayisi": kisi_sayisi,
        "oyuncular": {},
        "baslangic": datetime.now(),
        "bitis": datetime.now() + timedelta(minutes=sure_int),
        "mevcut_kelime": None
    }
    
    # Başlangıç mesajı
    embed = discord.Embed(
        title="🎉 İNGİLİZCE YARIŞ BAŞLADI!",
        description=f"**Seviye:** {seviye_str.upper()}\n**Süre:** {sure_int} dakika\n**Hedef:** {kisi_sayisi} katılımcı",
        color=discord.Color.green()
    )
    embed.add_field(
        name="📝 Nasıl Oynanır?",
        value="Verilen kelimeyi kullanarak İNGİLİZCE cümle kur!\nGrammar doğru olmalı!",
        inline=False
    )
    embed.add_field(
        name="🎯 Puanlama",
        value="• Her kelime = 1 puan\n• 10+ kelime = +5 bonus\n• 15+ kelime = +5 bonus\n• Virgül = +1",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)
    
    # İlk kelimeyi ver
    await yeni_kelime_ver(interaction.channel, kanal_id)
    
    # Süre bitince otomatik bitir
    await asyncio.sleep(sure_int * 60)
    if kanal_id in aktif_oyunlar:
        await oyun_bitir(interaction.channel, kanal_id)

async def yeni_kelime_ver(channel, kanal_id):
    """Yeni kelime verir"""
    if kanal_id not in aktif_oyunlar:
        return
    
    oyun = aktif_oyunlar[kanal_id]
    kelime = random.choice(KELIMELER[oyun["seviye"]])
    oyun["mevcut_kelime"] = kelime
    
    embed = discord.Embed(
        title="📝 YENİ KELİME",
        description=f"# {kelime.upper()}",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Bu kelimeyi kullanarak cümle kur!")
    
    await channel.send(embed=embed)

@bot.event
async def on_message(message):
    # Bot mesajlarını atla
    if message.author.bot:
        return
    
    kanal_id = message.channel.id
    
    # Aktif oyun var mı?
    if kanal_id not in aktif_oyunlar:
        await bot.process_commands(message)
        return
    
    oyun = aktif_oyunlar[kanal_id]
    
    # Süre kontrolü
    if datetime.now() > oyun["bitis"]:
        await oyun_bitir(message.channel, kanal_id)
        return
    
    # Komut değilse cümle olarak işle
    if not message.content.startswith("/"):
        await cumle_isle(message, kanal_id)
    
    await bot.process_commands(message)

async def cumle_isle(message, kanal_id):
    """Oyuncu cümlesini işler"""
    oyun = aktif_oyunlar[kanal_id]
    user_id = message.author.id
    cumle = message.content.strip()
    kelime = oyun.get("mevcut_kelime", "")
    
    if not kelime:
        return
    
    # Kelime var mı?
    if kelime.lower() not in cumle.lower():
        await message.add_reaction("❌")
        await message.reply(
            f"⚠️ **{kelime}** kelimesi cümlende yok!",
            delete_after=5
        )
        return
    
    # Minimum uzunluk
    if len(cumle.split()) < 3:
        await message.add_reaction("❌")
        await message.reply("⚠️ En az 3 kelime gerekli!", delete_after=5)
        return
    
    # GRAMMAR KONTROLÜ
    grammar = await grammar_kontrol(cumle)
    
    if grammar["hatali"]:
        await message.add_reaction("❌")
        
        # Hata detayları
        hata_mesaji = "**Grammar Hataları:**\n"
        for hata in grammar["hatalar"]:
            mesaj = hata.get("message", "Hata")
            
            # Düzeltme önerisi
            if hata.get("replacements"):
                dogru = hata["replacements"][0]["value"]
                hata_mesaji += f"• {mesaj}\n  ✅ **{dogru}** kullan\n"
            else:
                hata_mesaji += f"• {mesaj}\n"
        
        await message.reply(
            f"{hata_mesaji}\n⚠️ Puan alamadın!",
            delete_after=10
        )
        return
    
    # PUAN HESAPLA
    puan = puan_hesapla(cumle, kelime)
    
    # Oyuncu verisini güncelle
    if user_id not in oyun["oyuncular"]:
        oyun["oyuncular"][user_id] = {
            "isim": message.author.display_name,
            "puan": 0,
            "cumleler": [],
            "ilk_cumle": datetime.now()
        }
    
    oyun["oyuncular"][user_id]["puan"] += puan
    oyun["oyuncular"][user_id]["cumleler"].append({
        "cumle": cumle,
        "puan": puan,
        "zaman": datetime.now()
    })
    
    # BAŞARI MESAJI
    await message.add_reaction("✅")
    
    # Motivasyon
    if puan >= 15:
        motivasyon = random.choice(MOTIVASYON)
        mesaj_text = f"🌟💫✨ **MÜKEMMEL!** +{puan} puan!\n{motivasyon}"
    elif puan >= 10:
        mesaj_text = f"🎯 **Harika!** +{puan} puan!"
    else:
        mesaj_text = f"✅ +{puan} puan"
    
    await message.reply(mesaj_text, delete_after=5)
    
    # Yeni kelime
    await asyncio.sleep(1)
    await yeni_kelime_ver(message.channel, kanal_id)

@bot.tree.command(name="bitir", description="Yarışı bitir")
async def bitir_komut(interaction: discord.Interaction):
    kanal_id = interaction.channel_id
    
    if kanal_id not in aktif_oyunlar:
        await interaction.response.send_message(
            "❌ Aktif oyun yok!",
            ephemeral=True
        )
        return
    
    await interaction.response.send_message("⏹️ Oyun bitiriliyor...")
    await oyun_bitir(interaction.channel, kanal_id)

async def oyun_bitir(channel, kanal_id):
    """Oyunu bitirir ve sonuçları gösterir"""
    if kanal_id not in aktif_oyunlar:
        return
    
    oyun = aktif_oyunlar[kanal_id]
    oyuncular = oyun["oyuncular"]
    
    if not oyuncular:
        await channel.send("❌ Kimse cümle kurmadı!")
        del aktif_oyunlar[kanal_id]
        return
    
    # Sıralama
    siralama = sorted(
        oyuncular.items(),
        key=lambda x: x[1]["puan"],
        reverse=True
    )
    
    # Sonuç embed
    embed = discord.Embed(
        title="🏆 YARIŞ BİTTİ - SONUÇLAR",
        description=random.choice(MOTIVASYON),
        color=discord.Color.gold()
    )
    
    # Kazananlar
    madalyalar = ["🥇", "🥈", "🥉"]
    
    for i, (user_id, veri) in enumerate(siralama[:10]):
        madalya = madalyalar[i] if i < 3 else f"{i+1}."
        
        # İstatistikler
        cumle_sayisi = len(veri["cumleler"])
        toplam_sure = (datetime.now() - veri["ilk_cumle"]).total_seconds()
        ortalama = toplam_sure / cumle_sayisi if cumle_sayisi > 0 else 0
        
        dakika = int(toplam_sure // 60)
        saniye = int(toplam_sure % 60)
        
        embed.add_field(
            name=f"{madalya} {veri['isim']}",
            value=(
                f"**{veri['puan']} puan**\n"
                f"📝 {cumle_sayisi} cümle\n"
                f"⏱️ {dakika}:{saniye:02d} sürede\n"
                f"⚡ Ort: {ortalama:.1f}sn/cümle"
            ),
            inline=False
        )
    
    # Genel istatistikler
    toplam_cumle = sum(len(v["cumleler"]) for v in oyuncular.values())
    embed.set_footer(
        text=f"Toplam {toplam_cumle} cümle • LanguageTool ile kontrol edildi ✅"
    )
    
    await channel.send(embed=embed)
    
    # Oyunu sil
    del aktif_oyunlar[kanal_id]

@bot.tree.command(name="skor", description="Anlık skor tablosu")
async def skor(interaction: discord.Interaction):
    kanal_id = interaction.channel_id
    
    if kanal_id not in aktif_oyunlar:
        await interaction.response.send_message(
            "❌ Aktif oyun yok!",
            ephemeral=True
        )
        return
    
    oyun = aktif_oyunlar[kanal_id]
    oyuncular = oyun["oyuncular"]
    
    if not oyuncular:
        await interaction.response.send_message(
            "❌ Henüz kimse cümle kurmadı!",
            ephemeral=True
        )
        return
    
    # Sıralama
    siralama = sorted(
        oyuncular.items(),
        key=lambda x: x[1]["puan"],
        reverse=True
    )
    
    embed = discord.Embed(
        title="📊 ANLIK SKOR",
        color=discord.Color.blue()
    )
    
    for i, (user_id, veri) in enumerate(siralama, 1):
        embed.add_field(
            name=f"{i}. {veri['isim']}",
            value=f"**{veri['puan']}** puan • {len(veri['cumleler'])} cümle",
            inline=False
        )
    
    # Kalan süre
    kalan = (oyun["bitis"] - datetime.now()).total_seconds()
    if kalan > 0:
        dakika = int(kalan // 60)
        saniye = int(kalan % 60)
        embed.set_footer(text=f"⏱️ Kalan: {dakika}:{saniye:02d}")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="yardim", description="Komutları göster")
async def yardim(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📚 İngilizce Yarış Botu",
        description="Grammar kontrolü ile İngilizce pratik yap!",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🏁 Komutlar",
        value=(
            "`/yaris-basla [seviye] [süre] [kişi]` - Yarış başlat\n"
            "`/skor` - Anlık skorlar\n"
            "`/bitir` - Yarışı bitir\n"
            "`/yardim` - Bu mesaj"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎯 Nasıl Oynanır?",
        value=(
            "1. Yarış başlatılır\n"
            "2. Bot kelime verir\n"
            "3. O kelimeyi kullanarak cümle kur\n"
            "4. Grammar doğruysa puan kazan!"
        ),
        inline=False
    )
    
    embed.add_field(
        name="💰 Puanlama",
        value=(
            "• Her kelime = 1 puan\n"
            "• 10+ kelime = +5 bonus\n"
            "• 15+ kelime = +5 bonus\n"
            "• Virgül = +1 bonus"
        ),
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

import os
bot.run(os.getenv("DISCORD_TOKEN"))
