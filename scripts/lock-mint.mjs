import { readFileSync } from "fs";
import { Connection, Keypair, PublicKey } from "@solana/web3.js";
import { setAuthority, AuthorityType } from "@solana/spl-token";

const cfg = JSON.parse(readFileSync("C:\\Users\\ruben\\Documents\\optiloves-backend\\chain.config.json","utf8").replace(/^\uFEFF/,""));
const secret = Uint8Array.from(JSON.parse(readFileSync("C:\\Users\\ruben\\Documents\\optiloves-backend\\keys\\treasury.json","utf8")));
const kp = Keypair.fromSecretKey(secret);
const conn = new Connection(cfg.rpc, "confirmed");
const mint = new PublicKey(cfg.mint);

const sig = await setAuthority(conn, kp, mint, kp.publicKey, AuthorityType.MintTokens, null);
console.log("revoked mint authority, tx:", sig);